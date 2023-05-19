import base64
import hashlib
import hmac
import random
import string

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException
from sqlmodel import Session

from ..core.settings import Settings
from ..db.database import engine
from ..schema.user_tables.users import ChangePassword, Login, OnlyUsername

router = APIRouter()
session = Session(bind=engine)


client = boto3.client(
    "cognito-idp",
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
    excluded_chars = "/\\|_-"
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ""

    while len(password) < 14:
        char = random.choice(characters)
        if char not in excluded_chars:
            password += char

    return password


@router.post("/users/register/")
def register_user(user: OnlyUsername):
    try:
        client.admin_create_user(
            UserPoolId=Settings().cognito_pool_id,
            Username=user.username,
            TemporaryPassword=generate_password(),
            UserAttributes=[{"Name": "email", "Value": user.username}],
        )
    except client.exceptions.UsernameExistsException as e:
        print(e)
        raise HTTPException(status_code=400, detail="Username already exists")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Something went wrong")

    return {"message": "User created successfully"}


@router.put("/users/change-password/")
def change_password(user: ChangePassword):
    try:
        secret_hash = get_secret_hash(user.username)
        response = client.admin_initiate_auth(
            UserPoolId=Settings().cognito_pool_id,
            ClientId=Settings().cognito_client_id,
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={"USERNAME": user.username, "PASSWORD": user.temp_password, "SECRET_HASH": secret_hash},
        )
        if response["ChallengeName"] == "NEW_PASSWORD_REQUIRED":
            session = response["Session"]
            client.respond_to_auth_challenge(
                ClientId=Settings().cognito_client_id,
                ChallengeName="NEW_PASSWORD_REQUIRED",
                ChallengeResponses={
                    "USERNAME": user.username,
                    "NEW_PASSWORD": user.new_password,
                    "SECRET_HASH": secret_hash,
                },
                Session=session,
            )
        return {"message": "Password changed"}
    except client.exceptions.passwordExpired as e:
        if e.response["Error"]["Code"] == "ExpiredTemporaryPasswordException":
            return {"message": "Temporal password is expired, please request a new one"}
        else:
            return {"message": "There was an error trying to login"}


@router.post("/users/login/")
def login(user: Login):
    try:
        secret_hash = get_secret_hash(user.username)
        client.admin_initiate_auth(
            UserPoolId=Settings().cognito_pool_id,
            ClientId=Settings().cognito_client_id,
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={"USERNAME": user.username, "PASSWORD": user.password, "SECRET_HASH": secret_hash},
        )
        return {"message": "User logged on successfully"}
    except ClientError as e:
        if e.response["Error"]["Code"] == "ExpiredTemporaryPasswordException":
            return {"message": "Temporal password is expired, please request a new one"}
        else:
            return {"message": "There was an error trying to login"}


@router.post("/users/logoff/")
def logoff(user: OnlyUsername):
    try:
        client.admin_user_global_sign_out(UserPoolId=Settings().cognito_pool_id, Username=user.username)
    except ClientError as e:
        print(e)
        return {"message": "User was unable to log off"}
    return {"message": "User logged off successfully"}


@router.post("/users/reset-password/")
def reset_password(user: OnlyUsername):
    try:
        client.admin_reset_user_password(
            UserPoolId=Settings().cognito_pool_id, Username=user.username, ClientMetadata={"string": "string"}
        )
        return {"message": "Password reset successfully"}
    except Exception as e:
        print(e.message)
        return {"message": "There was an issue trying to change the password"}
