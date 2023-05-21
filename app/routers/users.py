from botocore.exceptions import ClientError
from fastapi import APIRouter, Header, HTTPException

from ..core.settings import Settings
from ..core.user_dependencies import (
    admin_create_user,
    client,
    get_secret_hash,
    initiate_auth,
    logout_user,
    respond_to_auth_challenge,
)
from ..schema.user_tables.users import BasicUser

router = APIRouter()


@router.post("/users/register/")
def register_user(user: BasicUser):
    try:
        admin_create_user(user.username)
    except client.exceptions.UsernameExistsException as e:
        print(e)
        raise HTTPException(status_code=400, detail="Username already exists")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Something went wrong")

    return {"message": "User created successfully"}


@router.put("/users/change-password/")
def change_password(user: BasicUser):
    try:
        response = initiate_auth(user.username, user.temp_password)
        if response["ChallengeName"] == "NEW_PASSWORD_REQUIRED":
            session = response["Session"]
            response = respond_to_auth_challenge(user.username, session, "NEW_PASSWORD_REQUIRED", user.password)
        return {"message": "Password changed"}
    except ClientError as e:
        print(e)
        if e.response["Error"]["Code"] == "ExpiredTemporaryPasswordException":
            return {"message": "Temporal password is expired, please request a new one"}
        else:
            return {"message": "There was an error trying to login"}


@router.post("/users/login/")
def login(user: BasicUser):
    try:
        response = initiate_auth(user.username, user.password)
        if "ChallengeName" in response:
            print(response["ChallengeName"])
            session = response["Session"]
            respond_to_auth_challenge(user.username, session, response["ChallengeName"])
        return {"message": "Logged in"}
    except ClientError as e:
        print(e)
        if e.response["Error"]["Code"] == "ExpiredTemporaryPasswordException":
            return {"message": "Temporal password is expired, please request a new one"}
        else:
            return {"message": "There was an error trying to login"}


@router.get("/users/logout/")
def logout(AccessToken: str = Header(None)):
    try:
        response = logout_user(AccessToken)
        print(response)
    except ClientError as e:
        print(e)
        return {"message": "User was unable to log off"}
    return {"message": "User logged off successfully"}


@router.post("/users/forgot-password/")
def forgot_password(user: BasicUser):
    try:
        response = client.forgot_password(
            ClientId=Settings().cognito_client_id, SecretHash=get_secret_hash(user.username), Username=user.username
        )
        print(response)
        return {"message": "An email with a reset link was sent to end user"}
    except Exception as e:
        print(e)
        return {"message": "There was an issue trying to change the password"}
