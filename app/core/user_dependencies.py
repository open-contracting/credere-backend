import base64
import hashlib
import hmac
import logging
import random
import string
from typing import Generator

import boto3

from app.schema.core import Application
from app.utils import email_utility

from ..core.settings import app_settings


def generate_password_fn():
    """
    Generates a random password of length at least 14 characters.
    The generated password includes characters from ASCII letters, digits and punctuation,
    but it excludes the following characters: '"/\\|_-#@%&*(){}[]<>~`'.

    :return: The randomly generated password.
    :rtype: str
    """
    excluded_chars = '"/\\|_-#@%&*(){}[]<>~`'
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ""

    while len(password) < 14:
        char = random.choice(characters)
        if char not in excluded_chars:
            password += char

    return password


class CognitoClient:
    """
    A client for AWS Cognito and SES services.

    Attributes:
        client: A boto3 client for Cognito
        ses: A boto3 client for SES
        generate_password: A function reference that generates a password

    """

    def __init__(
        self,
        cognitoClient,
        sesClient,
        generate_password_fn,
    ):
        self.client = cognitoClient
        self.ses = sesClient
        self.generate_password = generate_password_fn

    def exceptions(self):
        return self.client.exceptions

    def get_secret_hash(self, username):
        """
        Generates a secret hash for the given username using Cognito client secret and Cognito client id.

        Args:
            username: A string containing the username

        Returns:
            A base64 encoded string containing the generated secret hash.
        """
        app_client_id = app_settings.cognito_client_id
        key = app_settings.cognito_client_secret
        message = bytes(username + app_client_id, "utf-8")
        key = bytes(key, "utf-8")
        return base64.b64encode(
            hmac.new(key, message, digestmod=hashlib.sha256).digest()
        ).decode()

    def admin_create_user(self, username, name):
        """
        Creates a new user in AWS Cognito with the specified username and name. Sends an email to the new user
        with their temporary password.

        Args:
            username: A string containing the username of the new user (email format is expected).
            name: A string containing the name of the new user.

        Returns:
            A dictionary containing the response from the Cognito 'admin_create_user' method.

        Raises:
            boto3.exceptions: Any exceptions that occur when making the Cognito 'admin_create_user' request or sending the email. # noqa
        """
        temp_password = self.generate_password()
        responseCreateUser = self.client.admin_create_user(
            UserPoolId=app_settings.cognito_pool_id,
            Username=username,
            TemporaryPassword=temp_password,
            MessageAction="SUPPRESS",
            UserAttributes=[{"Name": "email", "Value": username}],
        )
        email_utility.send_mail_to_new_user(self.ses, name, username, temp_password)

        return responseCreateUser

    def verified_email(self, username):
        """
        Verifies the email of a user in AWS Cognito.

        Args:
            username: A string containing the username (email) of the user.

        Returns:
            A dictionary containing the response from the Cognito 'admin_update_user_attributes' method.

        Raises:
            boto3.exceptions: Any exceptions that occur when making the Cognito 'admin_update_user_attributes' request.
        """
        response = self.client.admin_update_user_attributes(
            UserPoolId=app_settings.cognito_pool_id,
            Username=username,
            UserAttributes=[
                {"Name": "email_verified", "Value": "true"},
            ],
        )

        return response

    def initiate_auth(self, username, password):
        """
        Initiates an authentication request for a user in AWS Cognito.

        Args:
            username: A string containing the username (typically an email) of the user initiating the authentication.
            password: A string containing the password of the user initiating the authentication.

        Returns:
            A dictionary containing the response from the Cognito 'initiate_auth' method, which includes the session expiration time if the authentication is successful. # noqa

        Raises:
            boto3.exceptions: Any exceptions that occur when making the Cognito 'initiate_auth' request.

        Notes:
            The 'initiate_auth' method uses 'USER_PASSWORD_AUTH' as the authentication flow, which requires a USERNAME, PASSWORD, and SECRET_HASH. # noqa
            The SECRET_HASH is generated using the 'get_secret_hash' method of this class.
        """
        secret_hash = self.get_secret_hash(username)
        response = self.client.initiate_auth(
            ClientId=app_settings.cognito_client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password,
                "SECRET_HASH": secret_hash,
            },
        )

        # Extract the session expiration time from the response
        if "AuthenticationResult" in response:
            authentication_result = response["AuthenticationResult"]
            if "ExpiresIn" in authentication_result:
                expiration_time = authentication_result["ExpiresIn"]
                logging.info("Session expiration time (in seconds):", expiration_time)

        return response

    def mfa_setup(self, session):
        """
        Sets up multi-factor authentication (MFA) for a user in AWS Cognito.

        Args:
            session: A string representing the session in which the user is currently authenticated.

        Returns:
            A dictionary containing a secret code for the Google Authenticator application and the updated session ID.

        Raises:
            boto3.exceptions: Any exceptions that occur when making the Cognito 'associate_software_token' request.

        Notes:
            The 'associate_software_token' method generates a secret code that is used to associate the user's AWS Cognito account with a multi-factor authentication app, such as Google Authenticator. # noqa
        """
        response = self.client.associate_software_token(Session=session)
        # Use this code in cmd to associate google authenticator with you account
        secret_code = response["SecretCode"]
        session = response["Session"]

        return {"secret_code": secret_code, "session": session}

    def verify_software_token(self, access_token, session, mfa_code):
        """
        Verifies a multi-factor authentication (MFA) code entered by the user in AWS Cognito.

        Args:
            access_token: A string representing the access token of the authenticated user.
            session: A string representing the session in which the user is currently authenticated.
            mfa_code: A string representing the MFA code that was entered by the user.

        Returns:
            A dictionary containing the response from the Cognito 'verify_software_token' method.

        Raises:
            boto3.exceptions: Any exceptions that occur when making the Cognito 'verify_software_token' request.

        Notes:
            The 'verify_software_token' method validates the MFA code provided by the user. If the code is valid, the method will return a successful response. # noqa
        """
        response = self.client.verify_software_token(
            AccessToken=access_token, Session=session, UserCode=mfa_code
        )

        return response

    def respond_to_auth_challenge(
        self, username, session, challenge_name, new_password="", mfa_code=""
    ):
        """
        Responds to the authentication challenge provided by AWS Cognito.

        Args:
            username: A string containing the username (email) of the user.
            session: A string representing the session in which the user is currently authenticated.
            challenge_name: A string representing the name of the challenge to respond to.
            new_password: A string containing the new password of the user. This is required if the challenge is 'NEW_PASSWORD_REQUIRED'.
            mfa_code: A string representing the MFA code that was entered by the user. This is required if the challenge is 'MFA_SETUP' or 'SOFTWARE_TOKEN_MFA'.# noqa

        Returns:
            A dictionary containing the response from the Cognito 'respond_to_auth_challenge' method.

        Raises:
            boto3.exceptions: Any exceptions that occur when making the Cognito 'respond_to_auth_challenge' request.

        Notes:
            The 'respond_to_auth_challenge' method allows the application to respond to different types of authentication challenges issued by AWS Cognito. # noqa
        """
        secret_hash = self.get_secret_hash(username)
        if challenge_name == "NEW_PASSWORD_REQUIRED":
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
        if challenge_name == "MFA_SETUP":
            response = self.client.associate_software_token(Session=session)
            access_token = response["SecretCode"]
            session = response["Session"]

            response = self.client.verify_software_token(
                AccessToken=access_token, Session=session, UserCode=mfa_code
            )
            session = response["Session"]
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
        if challenge_name == "SOFTWARE_TOKEN_MFA":
            response = self.client.respond_to_auth_challenge(
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
                "access_token": response["AuthenticationResult"]["AccessToken"],
                "refresh_token": response["AuthenticationResult"]["RefreshToken"],
            }

    def logout_user(self, access_token):
        """
        Logs out a user from all devices in AWS Cognito.

        Args:
            access_token: A string representing the access token of the user to log out.

        Returns:
            A dictionary containing the response from the Cognito 'admin_user_global_sign_out' method.

        Raises:
            boto3.exceptions: Any exceptions that occur when making the Cognito 'admin_user_global_sign_out' request.

        Notes:
            The 'admin_user_global_sign_out' method invalidates all refresh tokens issued to a user, which are required for the user to maintain access to authorized resources. The method should be used when the user logs out and chooses to log out from all devices. # noqa
        """
        response = self.client.get_user(AccessToken=access_token)
        username = None
        for attribute in response["UserAttributes"]:
            if attribute["Name"] == "sub":
                username = attribute["Value"]
                break
        response = self.client.admin_user_global_sign_out(
            UserPoolId=app_settings.cognito_pool_id, Username=username
        )

        return response

    def reset_password(self, username):
        """
        Resets the user's password.

        Args:
            username: A string containing the username (email) of the user.

        Returns:
            A dictionary containing the response from the Cognito 'admin_set_user_password' method.

        Side Effects:
            An email is sent to the user with the new temporary password.

        Raises:
            boto3.exceptions: Any exceptions that occur when making the Cognito 'admin_set_user_password' request.
        """
        temp_password = self.generate_password()

        responseSetPassword = self.client.admin_set_user_password(
            UserPoolId=app_settings.cognito_pool_id,
            Username=username,
            Password=temp_password,
            Permanent=False,
        )
        email_utility.send_mail_to_reset_password(self.ses, username, temp_password)

        return responseSetPassword

    def send_notifications_of_new_applications(
        self,
        ocp_email_group,
        lender_name,
        lender_email_group,
    ):
        """
        Sends notifications of new applications.

        Args:
            ocp_email_group: A list of email addresses representing the OCP email group.
            lender_name: A string representing the lender's name.
            lender_email_group: A list of email addresses representing the lender's email group.

        Side Effects:
            Sends an email notification to the lender's email group and to the OCP email group about the new application. # noqa

        Raises:
            boto3.exceptions: Any exceptions that occur when sending the emails.
        """
        email_utility.send_notification_new_app_to_fi(self.ses, lender_email_group)
        email_utility.send_notification_new_app_to_ocp(
            self.ses, ocp_email_group, lender_name
        )

    def send_request_to_sme(self, uuid, lender_name, email_message, sme_email):
        """
        Sends a request to the SME via email.

        Args:
            uuid: A string representing the unique identifier of the request.
            lender_name: A string representing the name of the lender.
            email_message: A string containing the email message to be sent.
            sme_email: A string representing the SME's email address.

        Returns:
            A string representing the message id of the sent email.

        Raises:
            boto3.exceptions: Any exceptions that occur when sending the email.
        """
        message_id = email_utility.send_mail_request_to_sme(
            self.ses, uuid, lender_name, email_message, sme_email
        )
        return message_id

    def send_rejected_email_to_sme(self, application, options):
        if options:
            message_id = email_utility.send_rejected_application_email(
                self.ses, application
            )
            return message_id
        message_id = email_utility.send_rejected_application_email_without_alternatives(
            self.ses, application
        )
        return message_id

    def send_application_approved_to_sme(self, application: Application):
        """
        Sends a rejection email to the SME, potentially with alternatives.

        Args:
            application: An object representing the application details.
            options: A boolean indicating if alternatives should be included in the rejection email.

        Returns:
            A string representing the message id of the sent email.

        Raises:
            boto3.exceptions: Any exceptions that occur when sending the email.
        """
        message_id = email_utility.send_application_approved_email(
            self.ses, application
        )
        return message_id

    def send_new_email_confirmation_to_sme(
        self,
        borrower_name: str,
        new_email: str,
        old_email: str,
        confirmation_email_token: str,
        application_uuid: str,
    ):
        """
        Sends an email confirmation message to a SME for a new email.

        Args:
            borrower_name: A string representing the name of the borrower.
            new_email: A string representing the new email address to be confirmed.
            old_email: A string representing the old email address.
            confirmation_email_token: A string representing the email confirmation token.
            application_uuid: A string representing the UUID of the application.

        Returns:
            A string representing the message id of the sent email.

        Raises:
            boto3.exceptions: Any exceptions that occur when sending the email.
        """
        return email_utility.send_new_email_confirmation(
            self.ses,
            borrower_name,
            new_email,
            old_email,
            confirmation_email_token,
            application_uuid,
        )

    def send_upload_contract_notifications(self, application):
        """
        Sends upload contract notifications to both the Financial Institution (FI) and the SME.

        Args:
            application: An application object containing details of the application.

        Returns:
            A tuple containing the message ids of the sent notifications, in the order: (FI_message_id, SME_message_id)

        Raises:
            boto3.exceptions: Any exceptions that occur when sending the notifications.
        """
        FI_message_id = email_utility.send_upload_contract_notification_to_FI(
            self.ses,
            application,
        )
        SME_message_id = email_utility.send_upload_contract_confirmation(
            self.ses,
            application,
        )

        return FI_message_id, SME_message_id

    def send_upload_documents_notifications(self, email: str):
        """
        Sends upload documents notifications to the Financial Institution (FI).

        Args:
            email: A string containing the email address where the notification will be sent.

        Returns:
            A string representing the message id of the sent notification.

        Raises:
            boto3.exceptions: Any exceptions that occur when sending the notification.
        """
        message_id = email_utility.send_upload_documents_notifications_to_FI(
            self.ses,
            email,
        )
        return message_id

    def send_copied_application_notifications(self, application):
        """
        Sends copied application notifications to the SME.

        Args:
            application: An application object containing information about the application that has been copied.

        Returns:
            A string representing the message id of the sent notification.

        Raises:
            boto3.exceptions: Any exceptions that occur when sending the notification.
        """
        return email_utility.send_copied_application_notification_to_sme(
            self.ses,
            application,
        )


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


def get_cognito_client() -> Generator:  # new
    yield cognito_client
