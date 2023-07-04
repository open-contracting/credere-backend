import logging
from typing import Union

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import app.utils.users as utils
from app.schema import api as ApiSchema
from app.utils.verify_token import get_current_user

from ..core.user_dependencies import CognitoClient, get_cognito_client
from ..db.session import get_db, transaction_session
from ..schema.core import BasicUser, SetupMFA, User

router = APIRouter()


@router.post("/users", tags=["users"], response_model=User)
async def create_user(
    payload: User,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(get_cognito_client),
):
    with transaction_session(session):
        try:
            user = User(**payload.dict())

            session.add(user)
            cognitoResponse = client.admin_create_user(payload.email, payload.name)
            user.external_id = cognitoResponse["User"]["Username"]

            return user
        except (client.exceptions().UsernameExistsException, IntegrityError) as e:
            logging.error(e)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Username already exists",
            )


@router.put(
    "/users/change-password",
    response_model=Union[ApiSchema.ChangePasswordResponse, ApiSchema.ResponseBase],
)
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

        client.verified_email(user.username)
        if (
            response.get("ChallengeName") is not None
            and response["ChallengeName"] == "MFA_SETUP"
        ):
            mfa_setup_response = client.mfa_setup(response["Session"])
            return ApiSchema.ChangePasswordResponse(
                detail="Password changed with MFA setup required",
                secret_code=mfa_setup_response["secret_code"],
                session=mfa_setup_response["session"],
                username=user.username,
            )

        return ApiSchema.ResponseBase(detail="Password changed")
    except ClientError as e:
        logging.error(e)
        if e.response["Error"]["Code"] == "ExpiredTemporaryPasswordException":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Temporal password is expired, please request a new one",
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="There was an error trying to update the password",
            )


@router.put("/users/setup-mfa", response_model=ApiSchema.ResponseBase)
def setup_mfa(
    user: SetupMFA,
    response: Response,
    client: CognitoClient = Depends(get_cognito_client),
):
    try:
        response = client.verify_software_token(
            user.secret, user.session, user.temp_password
        )
        logging.info(response)

        return ApiSchema.ResponseBase(detail="MFA configured successfully")
    except ClientError as e:
        logging.error(e)

        if e.response["Error"]["Code"] == "NotAuthorizedException":
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="Invalid session for the user, session is expired",
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="There was an error trying to setup mfa",
            )


@router.post(
    "/users/login",
    response_model=ApiSchema.LoginResponse,
)
def login(
    user: BasicUser,
    response: Response,
    client: CognitoClient = Depends(get_cognito_client),
    db: Session = Depends(get_db),
):
    try:
        response = client.initiate_auth(user.username, user.password)
        user = db.query(User).filter(User.email == user.username).first()

        return ApiSchema.LoginResponse(
            user=user,
            access_token=response["AuthenticationResult"]["AccessToken"],
            refresh_token=response["AuthenticationResult"]["RefreshToken"],
        )

    except ClientError as e:
        logging.error(e)

        if e.response["Error"]["Code"] == "ExpiredTemporaryPasswordException":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Temporal password is expired, please request a new one",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="There was an error trying to login",
            )


@router.post(
    "/users/login-mfa",
    response_model=ApiSchema.LoginResponse,
)
def login_mfa(
    user: BasicUser,
    client: CognitoClient = Depends(get_cognito_client),
    db: Session = Depends(get_db),
):
    try:
        response = client.initiate_auth(user.username, user.password)

        if "ChallengeName" in response:
            session = response["Session"]
            mfa_login_response = client.respond_to_auth_challenge(
                user.username,
                session,
                response["ChallengeName"],
                "",
                mfa_code=user.temp_password,
            )

            user = db.query(User).filter(User.email == user.username).first()

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                )

            return ApiSchema.LoginResponse(
                user=user,
                access_token=mfa_login_response["access_token"],
                refresh_token=mfa_login_response["refresh_token"],
            )

    except ClientError as e:
        logging.error(e)
        if e.response["Error"]["Code"] == "ExpiredTemporaryPasswordException":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Temporal password is expired, please request a new one",
            )

        elif e.response["Error"]["Code"] and e.response["Error"]["Message"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=e.response["Error"]["Message"],
            )


@router.get(
    "/users/logout",
    response_model=ApiSchema.ResponseBase,
)
def logout(
    Authorization: str = Header(None),
    client: CognitoClient = Depends(get_cognito_client),
):
    try:
        client.logout_user(Authorization)
    except ClientError as e:
        logging.error(e)
        # raise HTTPException(
        #     status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        #     detail="There was an error trying to logout",
        # )

    return ApiSchema.ResponseBase(detail="User logged out successfully")


@router.get(
    "/users/me",
    response_model=ApiSchema.UserResponse,
)
def me(
    usernameFromToken: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == usernameFromToken).first()
    return ApiSchema.UserResponse(user=user)


@router.post(
    "/users/forgot-password",
    response_model=ApiSchema.ResponseBase,
)
def forgot_password(
    user: BasicUser, client: CognitoClient = Depends(get_cognito_client)
):
    detail = "An email with a reset link was sent to end user"
    try:
        client.reset_password(user.username)

        return ApiSchema.ResponseBase(detail=detail)
    except Exception as e:
        logging.error(e)
        # always return 200 to avoid user enumeration
        return ApiSchema.ResponseBase(detail=detail)


@router.get("/users/{user_id}", tags=["users"], response_model=User)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.get("/users", tags=["users"], response_model=ApiSchema.UserListResponse)
async def get_all_users(db: Session = Depends(get_db)):
    return utils.get_all_users(db)
