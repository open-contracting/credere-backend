import boto3
from datetime import datetime
from pydantic import BaseModel
from functools import lru_cache
from fastapi import APIRouter, HTTPException
from sqlmodel import Session
from ..db.database import engine
from ..schema.user_tables.users import User
from ..core.settings import Settings
from botocore.exceptions import ClientError


router = APIRouter()
session = Session(bind=engine)

user = User(
    id=1,
    type="customer",
    email="jane@example.com",
    external_id="12345",
    fl_id=10,
    created_at=datetime.now(),
)


class NewUser(BaseModel):
    username: str
    password: str


client = boto3.client(
    "cognito-idp",
    region_name=Settings().cognito_aws_region,
    aws_access_key_id=Settings().access_key,
    aws_secret_access_key=Settings().client_secret,
)

# login, logout, recover password and set initial password to activate account.


@router.post("/users/register/")
def register_user(user: NewUser):
    try:
        response = client.admin_create_user(
            UserPoolId=Settings().cognito_pool_id,
            Username=user.username,
            TemporaryPassword=user.password,
            UserAttributes=[{"Name": "email", "Value": user.username}],
        )
        print(response)
    except client.exceptions.UsernameExistsException as e:
        raise HTTPException(status_code=400, detail="Username already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Something went wrong")

    return {"message": "User created successfully"}


@router.post("/users/login/")
def login(user: NewUser):
    try:
        response = client.admin_initiate_auth(
            UserPoolId=Settings().cognito_pool_id,
            ClientId=Settings().cognito_client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": user.username, "PASSWORD": user.password},
        )
        authentication_result = response["AuthenticationResult"]
        print("Access Token:", authentication_result["AccessToken"])
        print("Refresh Token:", authentication_result["RefreshToken"])
    except ClientError as e:
        print("Login failed:", e)

    return {"message": "User logged on successfully"}


@router.post("/users/logoff/")
def logoff(user: NewUser):
    try:
        response = client.admin_user_global_sign_out(UserPoolId=Settings().cognito_pool_id, Username=user.username)
        authentication_result = response["AuthenticationResult"]
        print("Access Token:", authentication_result["AccessToken"])
        print("Refresh Token:", authentication_result["RefreshToken"])
    except ClientError as e:
        print("Login failed:", e)
    return {"message": "User logged off successfully"}
