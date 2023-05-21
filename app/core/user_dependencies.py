import base64
import hashlib
import hmac
import random
import string

import boto3

from ..core.settings import Settings

client = boto3.client(
    "cognito-idp",
    region_name=Settings().cognito_aws_region,
    aws_access_key_id=Settings().access_key,
    aws_secret_access_key=Settings().client_secret,
)

ses = boto3.client(
    "ses",
    region_name=Settings().cognito_aws_region,
    aws_access_key_id=Settings().access_key,
    aws_secret_access_key=Settings().client_secret,
)


def get_secret_hash(username):
    app_client_id = Settings().cognito_client_id
    key = Settings().cognito_secret_key
    message = bytes(username + app_client_id, "utf-8")
    key = bytes(key, "utf-8")
    return base64.b64encode(hmac.new(key, message, digestmod=hashlib.sha256).digest()).decode()


def generate_password():
    excluded_chars = '"/\\|_-'
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ""

    while len(password) < 14:
        char = random.choice(characters)
        if char not in excluded_chars:
            password += char

    return password


def admin_create_user(username):
    return client.admin_create_user(
        UserPoolId=Settings().cognito_pool_id,
        Username=username,
        TemporaryPassword=generate_password(),
        UserAttributes=[{"Name": "email", "Value": username}],
    )


def initiate_auth(username, temp_password):
    secret_hash = get_secret_hash(username)
    response = client.initiate_auth(
        ClientId=Settings().cognito_client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": username, "PASSWORD": temp_password, "SECRET_HASH": secret_hash},
    )
    print(response)
    return response


def respond_to_auth_challenge(username, session, challenge_name, new_password="", mfa_code=""):
    secret_hash = get_secret_hash(username)
    if challenge_name == "NEW_PASSWORD_REQUIRED":
        return client.respond_to_auth_challenge(
            ClientId=Settings().cognito_client_id,
            ChallengeName=challenge_name,
            ChallengeResponses={
                "USERNAME": username,
                "NEW_PASSWORD": new_password,
                "SECRET_HASH": secret_hash,
            },
            Session=session,
        )
    if challenge_name == "MFA_SETUP":
        response = client.associate_software_token(Session=session)
        access_token = response["SecretCode"]
        session = response["Session"]

        print(access_token)  # Use this code in cmd to associate google authenticator with you account
        mfa_code = input("Enter MFA code: ")

        response = client.verify_software_token(AccessToken=access_token, Session=session, UserCode=mfa_code)
        session = response["Session"]
        return client.respond_to_auth_challenge(
            ClientId=Settings().cognito_client_id,
            ChallengeName=challenge_name,
            ChallengeResponses={
                "USERNAME": username,
                "NEW_PASSWORD": new_password,
                "SECRET_HASH": secret_hash,
            },
            Session=session,
        )
    if challenge_name == "SOFTWARE_TOKEN_MFA":
        mfa_code = input("Enter MFA code: ")
        response = client.respond_to_auth_challenge(
            ClientId=Settings().cognito_client_id,
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


def logout_user(access_token):
    response = client.get_user(AccessToken=access_token)
    username = None
    for attribute in response["UserAttributes"]:
        if attribute["Name"] == "sub":
            username = attribute["Value"]
            break
    response = client.admin_user_global_sign_out(UserPoolId=Settings().cognito_pool_id, Username=username)
    print(response)
    return response
