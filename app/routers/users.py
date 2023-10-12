import logging
from typing import Union

from botocore.exceptions import ClientError
from sqlalchemy.orm import Session

import app.utils.users as utils
from app.schema import api as ApiSchema
from app.utils.verify_token import get_current_user

from ..core.user_dependencies import CognitoClient, get_cognito_client
from ..db.session import get_db, transaction_session
from ..schema.core import BasicUser, SetupMFA, User, UserWithLender
from ..utils.permissions import OCP_only

from fastapi import APIRouter, Depends, Header  # isort:skip # noqa
from fastapi import HTTPException, Query, Response, status  # isort:skip # noqa

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/users", tags=["users"], response_model=User)
@OCP_only()
async def create_user(
    payload: User,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(get_cognito_client),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new user.

    This endpoint allows creating a new user. It is accessible only to users with the OCP role.

    :param payload: The user data for creating the new user.
    :type payload: User
    :param session: The database session dependency (automatically injected).
    :type session: Session
    :param client: The Cognito client dependency (automatically injected).
    :type client: CognitoClient
    :param current_user: The current user (automatically injected).
    :type current_user: User

    :return: The created user.
    :rtype: User
    """
    return utils.create_user(payload, session, client)


@router.put(
    "/users/change-password",
    response_model=Union[ApiSchema.ChangePasswordResponse, ApiSchema.ResponseBase],
)
def change_password(
    user: BasicUser,
    response: Response,
    client: CognitoClient = Depends(get_cognito_client),
):
    """
    Change user password.

    This endpoint allows users to change their password. It initiates the password change process
    and handles different scenarios such as new password requirement, MFA setup, and error handling.

    :param user: The user data including the username, temporary password, and new password.
    :type user: BasicUser
    :param response: The response object used to modify the response headers (automatically injected).
    :type response: Response
    :param client: The Cognito client dependency (automatically injected).
    :type client: CognitoClient

    :return: The change password response or an error response.
    :rtype: Union[ApiSchema.ChangePasswordResponse, ApiSchema.ResponseBase]
    """
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
        logger.exception(e)
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
    """
    Set up multi-factor authentication (MFA) for the user.

    This endpoint allows users to set up MFA using a software token. It verifies the software
    token with the provided secret, session, and temporary password.

    :param user: The user data including the secret code, session, and temporary password.
    :type user: SetupMFA
    :param response: The response object used to modify the response headers (automatically injected).
    :type response: Response
    :param client: The Cognito client dependency (automatically injected).
    :type client: CognitoClient

    :return: The response indicating successful MFA setup or an error response.
    :rtype: ApiSchema.ResponseBase
    """
    try:
        client.verify_software_token(user.secret, user.session, user.temp_password)

        return ApiSchema.ResponseBase(detail="MFA configured successfully")
    except ClientError as e:
        logger.exception(e)

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
    """
    Authenticate the user and generate access and refresh tokens.

    This endpoint handles user login and authentication. It initiates the
    authentication process using the provided username and password.
    If the authentication is successful, it returns the user information along with
    the generated access and refresh tokens.

    :param user: The user data including the username and password.
    :type user: BasicUser
    :param response: The response object used to modify the response headers (automatically injected).
    :type response: Response
    :param client: The Cognito client dependency (automatically injected).
    :type client: CognitoClient
    :param db: The database session dependency (automatically injected).
    :type db: Session

    :return: The response containing the user information and tokens if the login is successful.
    :rtype: ApiSchema.LoginResponse
    """
    try:
        response = client.initiate_auth(user.username, user.password)
        user = db.query(User).filter(User.email == user.username).first()

        return ApiSchema.LoginResponse(
            user=user,
            access_token=response["AuthenticationResult"]["AccessToken"],
            refresh_token=response["AuthenticationResult"]["RefreshToken"],
        )

    except ClientError as e:
        logger.exception(e)

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
    """
    Authenticate the user with Multi-Factor Authentication (MFA) and generate access and refresh tokens.

    This endpoint handles user login and authentication with MFA. It initiates the authentication
    process using the provided username and password. If the authentication process requires MFA,
    it responds to the MFA challenge by providing the MFA code. If the authentication is successful,
    it returns the user information along with the generated access and refresh tokens.

    :param user: The user data including the username, password, and MFA code.
    :type user: BasicUser
    :param client: The Cognito client dependency (automatically injected).
    :type client: CognitoClient
    :param db: The database session dependency (automatically injected).
    :type db: Session

    :return: The response containing the user information and tokens if the login is successful.
    :rtype: ApiSchema.LoginResponse
    """
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
        logger.exception(e)
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
    authorization: str = Header(None),
    client: CognitoClient = Depends(get_cognito_client),
):
    """
    Logout the user by invalidating the access token.

    This endpoint logs out the user by invalidating the provided access token.
    It extracts the access token from the Authorization header,
    invalidates the token using the Cognito client, and returns a response indicating
    successful logout.

    :param authorization: The Authorization header containing the access token.
    :type authorization: str
    :param client: The Cognito client dependency (automatically injected).
    :type client: CognitoClient

    :return: The response indicating successful logout.
    :rtype: ApiSchema.ResponseBase
    """
    try:
        access_token = authorization.split(" ")[1]
        client.logout_user(access_token)
    except ClientError as e:
        logger.exception(e)

    return ApiSchema.ResponseBase(detail="User logged out successfully")


@router.get(
    "/users/me",
    response_model=ApiSchema.UserResponse,
)
def me(
    usernameFromToken: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the details of the currently authenticated user.

    This endpoint retrieves the details of the currently authenticated user.
    It uses the username extracted from the JWT token to query the database
    and retrieve the user details.

    :param usernameFromToken: The username extracted from the JWT token.
    :type usernameFromToken: str
    :param db: The database session dependency (automatically injected).
    :type db: Session

    :return: The response containing the details of the authenticated user.
    :rtype: ApiSchema.UserResponse
    """
    user = db.query(User).filter(User.external_id == usernameFromToken).first()
    return ApiSchema.UserResponse(user=user)


@router.post(
    "/users/forgot-password",
    response_model=ApiSchema.ResponseBase,
)
def forgot_password(
    user: BasicUser, client: CognitoClient = Depends(get_cognito_client)
):
    """
    Initiate the process of resetting a user's password.

    This endpoint initiates the process of resetting a user's password.
    It sends an email to the user with a reset link that they can use to set a new password.

    :param user: The user information containing the username or email address of the user.
    :type user: BasicUser
    :param client: The Cognito client dependency (automatically injected).
    :type client: CognitoClient

    :return: The response indicating that an email with a reset link was sent to the user.
    :rtype: ApiSchema.ResponseBase
    """
    detail = "An email with a reset link was sent to end user"
    try:
        client.reset_password(user.username)

        return ApiSchema.ResponseBase(detail=detail)
    except Exception as e:
        logger.exception(e)
        # always return 200 to avoid user enumeration
        return ApiSchema.ResponseBase(detail=detail)


@router.get("/users/{user_id}", tags=["users"], response_model=User)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    Retrieve information about a user.

    This endpoint retrieves information about a user based on their user_id.

    :param user_id: The ID of the user.
    :type user_id: int
    :param db: The database session dependency (automatically injected).
    :type db: Session

    :return: The user information.
    :rtype: User
    :raises HTTPException 404: If the user is not found.
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.get("/users", tags=["users"], response_model=ApiSchema.UserListResponse)
@OCP_only()
async def get_all_users(
    page: int = Query(0, ge=0),
    page_size: int = Query(10, gt=0),
    sort_field: str = Query("created_at"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """
    Retrieve a list of users.

    This endpoint retrieves a list of users, paginated and sorted based on the provided parameters.

    :param page: The page number (0-based) to retrieve.
    :type page: int
    :param page_size: The number of users to retrieve per page.
    :type page_size: int
    :param sort_field: The field to sort the users by. Defaults to "created_at".
    :type sort_field: str
    :param sort_order: The sort order. Must be either "asc" or "desc". Defaults to "asc".
    :type sort_order: str
    :param current_user: The current user (automatically injected).
    :type current_user: User
    :param session: The database session dependency (automatically injected).
    :type session: Session

    :return: The paginated and sorted list of users.
    :rtype: ApiSchema.UserListResponse
    """
    return utils.get_all_users(page, page_size, sort_field, sort_order, session)


@router.put(
    "/users/{id}",
    tags=["users"],
    response_model=UserWithLender,
)
@OCP_only()
async def update_user(
    id: int,
    user: User,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """
    Update a user's information.

    This endpoint updates the information of a specific user identified by the provided ID.

    :param id: The ID of the user to update.
    :type id: int
    :param user: The updated user information.
    :type user: User
    :param current_user: The current user (automatically injected).
    :type current_user: User
    :param session: The database session dependency (automatically injected).
    :type session: Session

    :return: The updated user information.
    :rtype: UserWithLender
    """
    with transaction_session(session):
        return utils.update_user(session, user, id)
