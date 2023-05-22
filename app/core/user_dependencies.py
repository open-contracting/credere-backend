import base64
import hashlib
import hmac
import json
import random
import string

import boto3

from ..core.settings import Settings

client = boto3.client(
    "cognito-idp",
    region_name=Settings().aws_region,
    aws_access_key_id=Settings().aws_access_key,
    aws_secret_access_key=Settings().aws_client_secret,
)

ses = boto3.client(
    "ses",
    region_name=Settings().aws_region,
    aws_access_key_id=Settings().aws_access_key,
    aws_secret_access_key=Settings().aws_client_secret,
)


def get_secret_hash(username):
    app_client_id = Settings().cognito_client_id
    key = Settings().aws_client_secret
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


def admin_create_user(username, name):
    temp_password = generate_password()
    data = {
        "USER": name,
        "LINK-TO-WEB-VERSION": "www.google.com",
        "OCP_LOGO": "https://adrian-personal.s3.sa-east-1.amazonaws.com/logoocp.jpg",
        "SET_PASSWORD_IMAGE_LINK": "https://adrian-personal.s3.sa-east-1.amazonaws.com/set_password.png",
        "LOGIN_URL": Settings().frontend_url + "create-password/" + temp_password,
        "TWITTER_LOGO": "https://adrian-personal.s3.sa-east-1.amazonaws.com/twiterlogo.png",
        "FB_LOGO": "https://adrian-personal.s3.sa-east-1.amazonaws.com/facebook.png",
        "LINK_LOGO": "https://adrian-personal.s3.sa-east-1.amazonaws.com/link.png",
        "TWITTER_LINK": "www.google.com",
        "FACEBOOK_LINK": "www.google.com",
        "LINK_LINK": "www.google.com",
    }

    response = client.admin_create_user(
        UserPoolId=Settings().cognito_pool_id,
        Username=username,
        TemporaryPassword=temp_password,
        MessageAction="SUPPRESS",
        UserAttributes=[{"Name": "email", "Value": username}],
    )

    response = ses.send_templated_email(
        Source=Settings().email_sender_address,
        Destination={"ToAddresses": [Settings().email_sender_address]},
        Template="credere-NewAccountCreated",
        TemplateData=json.dumps(data),
    )
    return response


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
