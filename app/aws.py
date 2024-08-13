import base64
import hashlib
import hmac
import logging
import random
import string
from typing import Any, Callable

import boto3
from mypy_boto3_cognito_idp import CognitoIdentityProviderClient, literals, type_defs
from mypy_boto3_cognito_idp.client import Exceptions
from mypy_boto3_ses.client import SESClient

from app import mail
from app.models import Application, CreditProduct
from app.settings import app_settings

logger = logging.getLogger(__name__)


def generate_password_fn() -> str:
    """
    Generates a random password of length at least 14 characters.
    The generated password includes characters from ASCII letters, digits and punctuation,
    but it excludes the following characters: '"/\\|_-#@%&*(){}[]<>~`'.

    :return: The randomly generated password.
    """
    excluded_chars = '"/\\|_-#@%&*(){}[]<>~`'
    characters = f"{string.ascii_letters}{string.digits}{string.punctuation}"
    password = ""

    while len(password) < 14:
        char = random.choice(characters)
        if char not in excluded_chars:
            password += char

    return password


class CognitoClient:
    """
    A client for AWS Cognito and SES services.
    """

    def __init__(
        self,
        cognitoClient: CognitoIdentityProviderClient,
        sesClient: SESClient,
        generate_password_fn: Callable[[], str],
    ):
        #: A boto3 client for Cognito
        self.client = cognitoClient
        #: A boto3 client for SES
        self.ses = sesClient
        #: A function reference that generates a password
        self.generate_password = generate_password_fn

    @property
    def exceptions(self) -> Exceptions:
        return self.client.exceptions

    def get_secret_hash(self, username: str) -> str:
        """
        Generates a secret hash for the given username using Cognito client secret and Cognito client id.

        :param username: The username
        :return: A base64 encoded string containing the generated secret hash.
        """
        message = f"{username}{app_settings.cognito_client_id}".encode()
        key = app_settings.cognito_client_secret.encode()
        return base64.b64encode(hmac.new(key, message, digestmod=hashlib.sha256).digest()).decode()

    def admin_create_user(self, username: str, name: str) -> type_defs.AdminCreateUserResponseTypeDef:
        """
        Creates a new user in AWS Cognito with the specified username and name. Sends an email to the new user
        with their temporary password.

        :param username: The username of the new user (email format is expected).
        :param name: The name of the new user.
        :return: The response from the Cognito 'admin_create_user' method.
        :raises boto3.exceptions: Any exceptions that occur when making the Cognito request or sending the email.
        """
        temp_password = self.generate_password()

        response = self.client.admin_create_user(
            UserPoolId=app_settings.cognito_pool_id,
            Username=username,
            TemporaryPassword=temp_password,
            MessageAction="SUPPRESS",
            UserAttributes=[{"Name": "email", "Value": username}],
        )

        mail.send_mail_to_new_user(self.ses, name, username, temp_password)

        return response

    def verified_email(self, username: str) -> dict[str, Any]:
        """
        Verifies the email of a user in AWS Cognito.

        :param username: The username (email) of the user.
        :return: The response from the Cognito 'admin_update_user_attributes' method.
        :raises boto3.exceptions: Any exceptions that occur when making the Cognito request.
        """
        return self.client.admin_update_user_attributes(
            UserPoolId=app_settings.cognito_pool_id,
            Username=username,
            UserAttributes=[
                {"Name": "email_verified", "Value": "true"},
            ],
        )

    def initiate_auth(self, username: str, password: str) -> type_defs.InitiateAuthResponseTypeDef:
        """
        Initiates an authentication request for a user in AWS Cognito.

        :param username: The username (typically an email) of the user initiating authentication.
        :param password: The password of the user initiating the authentication.
        :return: The response from the Cognito 'initiate_auth' method, which includes the
                 session expiration time if the authentication is successful.
        :raises boto3.exceptions: Any exceptions that occur when making the Cognito request.

        Notes:
            The 'initiate_auth' method uses 'USER_PASSWORD_AUTH' as the authentication flow, which requires a USERNAME,
            PASSWORD, and SECRET_HASH. The SECRET_HASH is generated using the 'get_secret_hash' method of this class.
        """
        response = self.client.initiate_auth(
            ClientId=app_settings.cognito_client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password,
                "SECRET_HASH": self.get_secret_hash(username),
            },
        )

        # Extract the session expiration time from the response
        if "AuthenticationResult" in response:
            authentication_result = response["AuthenticationResult"]
            if "ExpiresIn" in authentication_result:
                expiration_time = authentication_result["ExpiresIn"]
                logger.info("Session expiration time (in seconds): %s", expiration_time)

        return response

    def mfa_setup(self, session: str) -> dict[str, str]:
        """
        Sets up multi-factor authentication (MFA) for a user in AWS Cognito.

        :param session: The session in which the user is currently authenticated.
        :return: A secret code for the Google Authenticator app and the updated session ID.
        :raises boto3.exceptions: Any exceptions that occur when making the Cognito request.

        Notes:
            The 'associate_software_token' method generates a secret code that is used to associate the user's AWS
            Cognito account with a multi-factor authentication app, such as Google Authenticator.
        """
        response = self.client.associate_software_token(Session=session)
        # Use this code in cmd to associate google authenticator with you account
        return {"secret_code": response["SecretCode"], "session": response["Session"]}

    def verify_software_token(
        self, access_token: str, session: str, mfa_code: str
    ) -> type_defs.VerifySoftwareTokenResponseTypeDef:
        """
        Verifies a multi-factor authentication (MFA) code entered by the user in AWS Cognito.

        :param access_token: The access token of the authenticated user.
        :param session: The session in which the user is currently authenticated.
        :param mfa_code: The MFA code that was entered by the user.
        :return: The response from the Cognito 'verify_software_token' method.
        :raises boto3.exceptions: Any exceptions that occur when making the Cognito request.

        Notes:
            The 'verify_software_token' method validates the MFA code provided by the user. If the code is valid, the
            method will return a successful response.
        """
        return self.client.verify_software_token(AccessToken=access_token, Session=session, UserCode=mfa_code)

    def respond_to_auth_challenge(
        self,
        username: str,
        session: str,
        challenge_name: literals.ChallengeNameTypeType,
        new_password: str = "",
        mfa_code: str = "",
    ) -> type_defs.RespondToAuthChallengeResponseTypeDef | dict[str, str]:
        """
        Responds to the authentication challenge provided by AWS Cognito.

        :param username: The username (email) of the user.
        :param session: The session in which the user is currently authenticated.
        :param challenge_name: The name of the challenge to respond to.
        :param new_password: The new password of the user. This is required if the challenge is
                             'NEW_PASSWORD_REQUIRED'.
        :param mfa_code: The MFA code that was entered by the user. This is required if the
                         challenge is 'MFA_SETUP' or 'SOFTWARE_TOKEN_MFA'.
        :return: The response from the Cognito 'respond_to_auth_challenge' method.
        :raises boto3.exceptions: Any exceptions that occur when making the Cognito request.

        Notes:
            The 'respond_to_auth_challenge' method allows the application to respond to different types of
            authentication challenges issued by AWS Cognito.
        """
        secret_hash = self.get_secret_hash(username)

        match challenge_name:
            case "NEW_PASSWORD_REQUIRED":
                return self.client.respond_to_auth_challenge(
                    ClientId=app_settings.cognito_client_id,
                    ChallengeName=challenge_name,
                    ChallengeResponses={
                        "USERNAME": username,
                        "NEW_PASSWORD": new_password,
                        "SECRET_HASH": secret_hash,
                    },
                    Session=session,
                )
            case "MFA_SETUP":
                associate_response = self.client.associate_software_token(Session=session)

                verify_response = self.client.verify_software_token(
                    AccessToken=associate_response["SecretCode"],
                    Session=associate_response["Session"],
                    UserCode=mfa_code,
                )

                return self.client.respond_to_auth_challenge(
                    ClientId=app_settings.cognito_client_id,
                    ChallengeName=challenge_name,
                    ChallengeResponses={
                        "USERNAME": username,
                        "NEW_PASSWORD": new_password,
                        "SECRET_HASH": secret_hash,
                    },
                    Session=verify_response["Session"],
                )
            case "SOFTWARE_TOKEN_MFA":
                challenge_response = self.client.respond_to_auth_challenge(
                    ClientId=app_settings.cognito_client_id,
                    ChallengeName=challenge_name,
                    ChallengeResponses={
                        "USERNAME": username,
                        "SOFTWARE_TOKEN_MFA_CODE": mfa_code,
                        "SECRET_HASH": secret_hash,
                    },
                    Session=session,
                )

                return {
                    "access_token": challenge_response["AuthenticationResult"]["AccessToken"],
                    "refresh_token": challenge_response["AuthenticationResult"]["RefreshToken"],
                }
            case _:
                raise NotImplementedError

    def reset_password(self, username: str) -> dict[str, Any]:
        """
        Resets the user's password.

        An email is sent to the user with the new temporary password.

        :param username: The username (email) of the user.
        :return: The response from the Cognito 'admin_set_user_password' method.
        :raises boto3.exceptions: Any exceptions that occur when making the Cognito request.
        """
        temp_password = self.generate_password()

        response = self.client.admin_set_user_password(
            UserPoolId=app_settings.cognito_pool_id,
            Username=username,
            Password=temp_password,
            Permanent=False,
        )

        mail.send_mail_to_reset_password(self.ses, username, temp_password)

        return response

    def send_notifications_of_new_applications(
        self,
        ocp_email_group: str,
        lender_name: str,
        lender_email_group: str,
    ) -> None:
        """
        Sends notifications of new applications.

        Sends an email notification to the lender's email group and to the OCP email group about the new application.

        :param ocp_email_group: A list of email addresses representing the OCP email group.
        :param lender_name: The lender's name.
        :param lender_email_group: A list of email addresses representing the lender's email group.
        :raises boto3.exceptions: Any exceptions that occur when sending the emails.
        """
        mail.send_notification_new_app_to_fi(self.ses, lender_email_group)
        mail.send_notification_new_app_to_ocp(self.ses, ocp_email_group, lender_name)

    def send_request_to_sme(self, uuid: str, lender_name: str, email_message: str, sme_email: str) -> str:
        """
        Sends a request to the SME via email.

        :param uuid: The unique identifier of the request.
        :param lender_name: The name of the lender.
        :param email_message: The email message to be sent.
        :param sme_email: The SME's email address.
        :return: The message id of the sent email.
        :raises boto3.exceptions: Any exceptions that occur when sending the email.
        """
        return mail.send_mail_request_to_sme(self.ses, uuid, lender_name, email_message, sme_email)

    def send_rejected_email_to_sme(self, application: Application, options: list[CreditProduct]) -> str:
        """
        Sends a rejection email to the SME, potentially with alternatives.

        :param application: The application details.
        :param options: The alternatives to be included in the rejection email.
        :return: The message id of the sent email.
        :raises boto3.exceptions: Any exceptions that occur when sending the email.
        """
        if options:
            return mail.send_rejected_application_email(self.ses, application)
        return mail.send_rejected_application_email_without_alternatives(self.ses, application)

    def send_application_approved_to_sme(self, application: Application) -> str:
        """
        Sends a approved confirmation email to the SME.

        :param application: The application details.
        :return: The message id of the sent email.
        :raises boto3.exceptions: Any exceptions that occur when sending the email.
        """
        return mail.send_application_approved_email(self.ses, application)

    def send_application_submission_completed(self, application: Application) -> str:
        """
        Sends a submission confirmation email to the SME.

        :param application: The application details.
        :return: The message id of the sent email.
        :raises boto3.exceptions: Any exceptions that occur when sending the email.
        """
        return mail.send_application_submission_completed(self.ses, application)

    def send_application_credit_disbursed(self, application: Application) -> str:
        """
        Sends a credit disbursed confirmation email to the SME.

        :param application: The application details.
        :return: The message id of the sent email.
        :raises boto3.exceptions: Any exceptions that occur when sending the email.
        """
        return mail.send_application_credit_disbursed(self.ses, application)

    def send_new_email_confirmation_to_sme(
        self,
        borrower_name: str,
        new_email: str,
        old_email: str,
        confirmation_email_token: str,
        application_uuid: str,
    ) -> str:
        """
        Sends an email confirmation message to a SME for a new email.

        :param borrower_name: The name of the borrower.
        :param new_email: The new email address to be confirmed.
        :param old_email: The old email address.
        :param confirmation_email_token: The email confirmation token.
        :param application_uuid: The UUID of the application.
        :return: The message id of the sent email.
        :raises boto3.exceptions: Any exceptions that occur when sending the email.
        """
        return mail.send_new_email_confirmation(
            self.ses, borrower_name, new_email, old_email, confirmation_email_token, application_uuid
        )

    def send_upload_contract_notifications(self, application: Application) -> tuple[str, str]:
        """
        Sends upload contract notifications to both the Financial Institution (FI) and the SME.

        :param application: An application object containing details of the application.
        :return: The message ids of the sent notifications: (FI_message_id, SME_message_id)
        :raises boto3.exceptions: Any exceptions that occur when sending the notifications.
        """
        return (
            mail.send_upload_contract_notification_to_fi(self.ses, application),
            mail.send_upload_contract_confirmation(self.ses, application),
        )

    def send_upload_documents_notifications(self, email: str) -> str:
        """
        Sends upload documents notifications to the Financial Institution (FI).

        :param email: The email address where the notification will be sent.
        :return: The message id of the sent notification.
        :raises boto3.exceptions: Any exceptions that occur when sending the notification.
        """
        return mail.send_upload_documents_notifications_to_fi(self.ses, email)

    def send_copied_application_notifications(self, application: Application) -> str:
        """
        Sends copied application notifications to the SME.

        :param application: An application object containing information about the application that has been copied.
        :return: The message id of the sent notification.
        :raises boto3.exceptions: Any exceptions that occur when sending the notification.
        """
        return mail.send_copied_application_notification_to_sme(self.ses, application)


cognito = boto3.client(
    "cognito-idp",
    region_name=app_settings.aws_region,
    aws_access_key_id=app_settings.aws_access_key,
    aws_secret_access_key=app_settings.aws_client_secret,
)

sesClient = boto3.client(
    "ses",
    region_name=app_settings.aws_region,
    aws_access_key_id=app_settings.aws_access_key,
    aws_secret_access_key=app_settings.aws_client_secret,
)

cognito_client = CognitoClient(
    cognito,
    sesClient,
    generate_password_fn,
)
