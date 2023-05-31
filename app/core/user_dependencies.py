import base64
import hashlib
import hmac
import json
import random
import string
from typing import Generator
from urllib.parse import quote

import boto3

from app.email_templates import NEW_USER_TEMPLATE_NAME

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
        data = {
            "USER": name,
            "LINK-TO-WEB-VERSION": "www.google.com",
            "OCP_LOGO": "https://adrian-personal.s3.sa-east-1.amazonaws.com/logoocp.jpg",
            "SET_PASSWORD_IMAGE_LINK": "https://adrian-personal.s3.sa-east-1.amazonaws.com/set_password.png",
            "LOGIN_URL": app_settings.frontend_url
            + "/create-password?key="
            + quote(temp_password)
            + "&email="
            + quote(username),
            "TWITTER_LOGO": "https://adrian-personal.s3.sa-east-1.amazonaws.com/twiterlogo.png",
            "FB_LOGO": "https://adrian-personal.s3.sa-east-1.amazonaws.com/facebook.png",
            "LINK_LOGO": "https://adrian-personal.s3.sa-east-1.amazonaws.com/link.png",
            "TWITTER_LINK": "www.google.com",
            "FACEBOOK_LINK": "www.google.com",
            "LINK_LINK": "www.google.com",
        }

        response = self.client.admin_create_user(
            UserPoolId=app_settings.cognito_pool_id,
            Username=username,
            TemporaryPassword=temp_password,
            MessageAction="SUPPRESS",
            UserAttributes=[{"Name": "email", "Value": username}],
        )

        response = self.ses.send_templated_email(
            Source=app_settings.email_sender_address,
            Destination={"ToAddresses": [username]},
            Template=NEW_USER_TEMPLATE_NAME,
            TemplateData=json.dumps(data),
        )

        return response

    def verified_email(self, username):
        response = self.client.admin_update_user_attributes(
            UserPoolId=app_settings.cognito_pool_id,
            Username=username,
            UserAttributes=[
                {"Name": "email_verified", "Value": "true"},
            ],
        )

        print(response)
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
        print("USER_PASSWORD_AUTH")
        print(response)
        # Extract the session expiration time from the response
        if "AuthenticationResult" in response:
            authentication_result = response["AuthenticationResult"]
            if "ExpiresIn" in authentication_result:
                expiration_time = authentication_result["ExpiresIn"]
                print("Session expiration time (in seconds):", expiration_time)

        return response

    def mfa_setup(self, session):
        response = self.client.associate_software_token(Session=session)
        secret_code = response["SecretCode"]
        session = response["Session"]

        # Use this code in cmd to associate google authenticator with you account
        print(secret_code)
        print(response)

        return {"secret_code": secret_code, "session": session}

    def verify_software_token(self, access_token, session, mfa_code):
        response = self.client.verify_software_token(
            AccessToken=access_token, Session=session, UserCode=mfa_code
        )

        print("verify_software_token")
        print(response)
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

            print(
                access_token
            )  # Use this code in cmd to associate google authenticator with you account
            # mfa_code = input("Enter MFA code: ")

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
            # mfa_code = input("Enter MFA code: ")
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
            print(response["AuthenticationResult"]["AccessToken"])
            return response["AuthenticationResult"]["AccessToken"]

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
        print(response)
        return response

    def reset_password(self, username):
        temp_password = self.generate_password()
        data = {
            "USER": "UserName",  # change for actual name
            "LINK-TO-WEB-VERSION": "www.google.com",
            "OCP_LOGO": "https://adrian-personal.s3.sa-east-1.amazonaws.com/logoocp.jpg",
            "USER_ACCOUNT": username,
            "RESET_PASSWORD_URL": app_settings.frontend_url
            + "/create-password?key="
            + quote(temp_password)
            + "&email="
            + quote(username),
            "RESET_PASSWORD_IMAGE": "https://adrian-personal.s3.sa-east-1.amazonaws.com/ResetPassword.png",
            "TWITTER_LOGO": "https://adrian-personal.s3.sa-east-1.amazonaws.com/twiterlogo.png",
            "FB_LOGO": "https://adrian-personal.s3.sa-east-1.amazonaws.com/facebook.png",
            "LINK_LOGO": "https://adrian-personal.s3.sa-east-1.amazonaws.com/link.png",
            "TWITTER_LINK": "www.google.com",
            "FACEBOOK_LINK": "www.google.com",
            "LINK_LINK": "www.google.com",
        }

        response = self.client.admin_set_user_password(
            UserPoolId=app_settings.cognito_pool_id,
            Username=username,
            Password=temp_password,
            Permanent=False,
        )

        print(response)

        response = self.ses.send_templated_email(
            Source=app_settings.email_sender_address,
            Destination={"ToAddresses": [username]},
            Template="credere-ResetPassword",
            TemplateData=json.dumps(data),
        )

        print(response)

        return response


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
    try:
        print("get_cognito_client")
        yield cognito_client
    finally:
        print("Closing cognito client")
        cognito.close()
