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
    excluded_chars = '"/\\|_-#@%&*(){}[]<>~`'
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ""

    while len(password) < 14:
        char = random.choice(characters)
        if char not in excluded_chars:
            password += char

    return password


class CognitoClient:
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
        app_client_id = app_settings.cognito_client_id
        key = app_settings.cognito_client_secret
        message = bytes(username + app_client_id, "utf-8")
        key = bytes(key, "utf-8")
        return base64.b64encode(
            hmac.new(key, message, digestmod=hashlib.sha256).digest()
        ).decode()

    def admin_create_user(self, username, name):
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
        response = self.client.admin_update_user_attributes(
            UserPoolId=app_settings.cognito_pool_id,
            Username=username,
            UserAttributes=[
                {"Name": "email_verified", "Value": "true"},
            ],
        )

        return response

    def initiate_auth(self, username, password):
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
        response = self.client.associate_software_token(Session=session)
        # Use this code in cmd to associate google authenticator with you account
        secret_code = response["SecretCode"]
        session = response["Session"]

        return {"secret_code": secret_code, "session": session}

    def verify_software_token(self, access_token, session, mfa_code):
        response = self.client.verify_software_token(
            AccessToken=access_token, Session=session, UserCode=mfa_code
        )

        return response

    def respond_to_auth_challenge(
        self, username, session, challenge_name, new_password="", mfa_code=""
    ):
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
        email_utility.send_notification_new_app_to_fi(self.ses, lender_email_group)
        email_utility.send_notification_new_app_to_ocp(
            self.ses, ocp_email_group, lender_name
        )

    def send_request_to_sme(self, uuid, lender_name, email_message, sme_email):
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
        return email_utility.send_new_email_confirmation(
            self.ses,
            borrower_name,
            new_email,
            old_email,
            confirmation_email_token,
            application_uuid,
        )

    def send_upload_contract_notifications(self, application):
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
        message_id = email_utility.send_upload_documents_notifications_to_FI(
            self.ses,
            email,
        )
        return message_id

    def send_copied_application_notifications(self, application):
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
