from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.user_dependencies import CognitoClient, get_cognito_client
from ..db.session import get_db
from ..schema.core import BasicUser, SetupMFA, User

router = APIRouter()


@router.get("/users/{user_id}", tags=["users"], response_model=User)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    print(user_id)
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/users", tags=["users"], response_model=User)
async def create_user(
    payload: User,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(get_cognito_client),
):
    try:
        print(payload)
        user = User(**payload.dict())
        print(session)
        session.add(user)
        session.commit()
        session.refresh(user)
        cognitoResponse = client.admin_create_user(payload.email, payload.name)
        print(cognitoResponse)
        user.external_id = cognitoResponse["User"]["Username"]
        print(user)
        return user
    except (client.exceptions().UsernameExistsException, IntegrityError) as e:
        print(e)
        raise HTTPException(status_code=400, detail="Username already exists")


@router.post("/users/register")
def register_user(user: BasicUser, client: CognitoClient = Depends(get_cognito_client)):
    try:
        response = client.admin_create_user(user.username, user.name)
        print(response)
    except client.exceptions().UsernameExistsException as e:
        print(e)
        raise HTTPException(status_code=400, detail="Username already exists")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Something went wrong")


@router.put("/users/change-password")
def change_password(
    user: BasicUser,
    response: Response,
    client: CognitoClient = Depends(get_cognito_client),
):
    try:
        response = client.initiate_auth(user.username, user.temp_password)
        if response["ChallengeName"] == "NEW_PASSWORD_REQUIRED":
            session = response["Session"]
            response = client.respond_to_auth_challenge(
                user.username, session, "NEW_PASSWORD_REQUIRED", user.password
            )

        print(response)

        client.verified_email(user.username)
        if (
            response.get("ChallengeName") is not None
            and response["ChallengeName"] == "MFA_SETUP"
        ):
            mfa_setup_response = client.mfa_setup(response["Session"])
            return {
                "message": "Password changed with MFA setup required",
                "secret_code": mfa_setup_response["secret_code"],
                "session": mfa_setup_response["session"],
                "username": user.username,
            }

        return {"message": "Password changed"}
    except ClientError as e:
        print(e)
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        if e.response["Error"]["Code"] == "ExpiredTemporaryPasswordException":
            return {"message": "Temporal password is expired, please request a new one"}
        else:
            return {"message": "There was an error trying to update the password"}


@router.put("/users/setup-mfa")
def setup_mfa(
    user: SetupMFA,
    response: Response,
    client: CognitoClient = Depends(get_cognito_client),
):
    try:
        response = client.verify_software_token(
            user.secret, user.session, user.temp_password
        )
        print(response)

        return {"message": "MFA configured successfully"}
    except ClientError as e:
        print(e)
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        if e.response["Error"]["Code"] == "NotAuthorizedException":
            return {"message": "Invalid session for the user, session is expired"}
        else:
            return {"message": "There was an error trying to setup mfa"}


@router.post("/users/login")
def login(
    user: BasicUser,
    response: Response,
    client: CognitoClient = Depends(get_cognito_client),
):
    try:
        response = client.initiate_auth(user.username, user.password)

        # todo load user from db
        return {
            "user": {"email": user.username, "name": "User"},
            "access_token": response["AuthenticationResult"]["AccessToken"],
        }
    except ClientError as e:
        print(e)
        response.status_code = status.HTTP_401_UNAUTHORIZED
        if e.response["Error"]["Code"] == "ExpiredTemporaryPasswordException":
            return {"message": "Temporal password is expired, please request a new one"}
        else:
            return {"message": "There was an error trying to login"}


@router.post("/users/login-mfa")
def login_mfa(user: BasicUser, client: CognitoClient = Depends(get_cognito_client)):
    try:
        response = client.initiate_auth(user.username, user.password)
        if "ChallengeName" in response:
            print(response["ChallengeName"])
            session = response["Session"]
            access_token = client.respond_to_auth_challenge(
                user.username,
                session,
                response["ChallengeName"],
                "",
                mfa_code=user.temp_password,
            )
            print(access_token)

            # todo load user from db
            return {
                "user": {"email": user.username, "name": "User"},
                "access_token": access_token,
            }

    except ClientError as e:
        print(e)
        if e.response["Error"]["Code"] == "ExpiredTemporaryPasswordException":
            return {"message": "Temporal password is expired, please request a new one"}
        else:
            return {"message": "There was an error trying to login"}


@router.get("/users/logout")
def logout(
    Authorization: str = Header(None),
    client: CognitoClient = Depends(get_cognito_client),
):
    try:
        response = client.logout_user(Authorization)
        print(response)
    except ClientError as e:
        print(e)
        return {"message": "User was unable to logout"}

    return {"message": "User logged out successfully"}


@router.get("/users/me")
def me(
    response: Response,
    Authorization: str = Header(None),
    client: CognitoClient = Depends(get_cognito_client),
):
    try:
        response = client.get_user(AccessToken=Authorization)
        for item in response["UserAttributes"]:
            if item["Name"] == "email":
                email_value = item["Value"]
                break

        return {"user": {"email": email_value, "name": "User"}}
    except ClientError as e:
        print(e)
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"message": "User not found"}


@router.post("/users/forgot-password")
def forgot_password(
    user: BasicUser, client: CognitoClient = Depends(get_cognito_client)
):
    try:
        response = client.reset_password(user.username)
        print(response)
        return {"message": "An email with a reset link was sent to end user"}
    except Exception as e:
        print(e)
        return {"message": "There was an issue trying to change the password"}
