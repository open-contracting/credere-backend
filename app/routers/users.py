import logging

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app import dependencies, models, serializers
from app.aws import CognitoClient
from app.db import get_db, rollback_on_error
from app.util import SortOrder, commit_and_refresh, get_object_or_404, get_order_by

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/users",
    tags=["users"],
)
async def create_user(
    payload: models.User,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(dependencies.get_cognito_client),
    admin: models.User = Depends(dependencies.get_admin_user),
) -> models.User:
    """
    Create a new user.

    This endpoint allows creating a new user. It is accessible only to users with the OCP role.

    :param payload: The user data for creating the new user.
    :return: The created user.
    """
    with rollback_on_error(session):
        try:
            user = models.User.create(session, **payload.model_dump())
            cognito_response = client.admin_create_user(payload.email, payload.name)
            user.external_id = cognito_response["User"]["Username"]

            return commit_and_refresh(session, user)
        except (client.exceptions().UsernameExistsException, IntegrityError) as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Username already exists",
            )


@router.put(
    "/users/change-password",
)
def change_password(
    user: models.BasicUser,
    client: CognitoClient = Depends(dependencies.get_cognito_client),
) -> serializers.ChangePasswordResponse | serializers.ResponseBase:
    """
    Change user password.

    This endpoint allows users to change their password. It initiates the password change process
    and handles different scenarios such as new password requirement, MFA setup, and error handling.

    :param user: The user data including the username, temporary password, and new password.
    :param response: The response object used to modify the response headers (automatically injected).
    :return: The change password response or an error response.
    """
    try:
        response = client.initiate_auth(user.username, user.temp_password)
        if response["ChallengeName"] == "NEW_PASSWORD_REQUIRED":
            session = response["Session"]
            response = client.respond_to_auth_challenge(
                username=user.username,
                session=session,
                challenge_name="NEW_PASSWORD_REQUIRED",
                new_password=user.password,
            )

        client.verified_email(user.username)
        if response.get("ChallengeName") is not None and response["ChallengeName"] == "MFA_SETUP":
            mfa_setup_response = client.mfa_setup(response["Session"])

            return serializers.ChangePasswordResponse(
                detail="Password changed with MFA setup required",
                secret_code=mfa_setup_response["secret_code"],
                session=mfa_setup_response["session"],
                username=user.username,
            )

        return serializers.ResponseBase(detail="Password changed")
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


@router.put(
    "/users/setup-mfa",
)
def setup_mfa(
    user: models.SetupMFA,
    client: CognitoClient = Depends(dependencies.get_cognito_client),
) -> serializers.ResponseBase:
    """
    Set up multi-factor authentication (MFA) for the user.

    This endpoint allows users to set up MFA using a software token. It verifies the software
    token with the provided secret, session, and temporary password.

    :param user: The user data including the secret code, session, and temporary password.
    :param response: The response object used to modify the response headers (automatically injected).
    :return: The response indicating successful MFA setup or an error response.
    """
    try:
        client.verify_software_token(user.secret, user.session, user.temp_password)

        return serializers.ResponseBase(detail="MFA configured successfully")
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
)
def login(
    user: models.BasicUser,
    client: CognitoClient = Depends(dependencies.get_cognito_client),
    session: Session = Depends(get_db),
) -> serializers.LoginResponse:
    """
    Authenticate the user with Multi-Factor Authentication (MFA) and generate access and refresh tokens.

    This endpoint handles user login and authentication with MFA. It initiates the authentication
    process using the provided username and password. If the authentication process requires MFA,
    it responds to the MFA challenge by providing the MFA code. If the authentication is successful,
    it returns the user information along with the generated access and refresh tokens.

    :param user: The user data including the username, password, and MFA code.
    :return: The response containing the user information and tokens if the login is successful.
    """
    try:
        db_user = get_object_or_404(session, models.User, "email", user.username)
        response = client.initiate_auth(user.username, user.password)

        if "ChallengeName" in response:
            mfa_login_response = client.respond_to_auth_challenge(
                username=user.username,
                session=response["Session"],
                challenge_name=response["ChallengeName"],
                mfa_code=user.temp_password,
            )

            return serializers.LoginResponse(
                user=db_user,
                access_token=mfa_login_response["access_token"],
                refresh_token=mfa_login_response["refresh_token"],
            )
        else:
            raise NotImplementedError
    except ClientError as e:
        logger.exception(e)
        # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/error-handling.html#parsing-error-responses-and-catching-exceptions-from-aws-services
        if e.response["Error"]["Code"] == "ExpiredTemporaryPasswordException":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Temporal password is expired, please request a new one",
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=e.response["Error"]["Message"],
            )


@router.get(
    "/users/logout",
)
def logout(
    authorization: str = Header(None),
    client: CognitoClient = Depends(dependencies.get_cognito_client),
) -> serializers.ResponseBase:
    """
    Logout the user by invalidating the access token.

    This endpoint logs out the user by invalidating the provided access token.
    It extracts the access token from the Authorization header,
    invalidates the token using the Cognito client, and returns a response indicating
    successful logout.

    :param authorization: The Authorization header containing the access token.
    :return: The response indicating successful logout.
    """
    try:
        client.logout_user(authorization.split(" ")[1])
    except ClientError as e:
        logger.exception(e)

    return serializers.ResponseBase(detail="User logged out successfully")


@router.get(
    "/users/me",
)
def me(
    username_from_token: str = Depends(dependencies.get_current_user),
    session: Session = Depends(get_db),
) -> serializers.UserResponse:
    """
    Get the details of the currently authenticated user.

    This endpoint retrieves the details of the currently authenticated user.
    It uses the username extracted from the JWT token to query the database
    and retrieve the user details.

    :param username_from_token: The username extracted from the JWT token.
    :return: The response containing the details of the authenticated user.
    """
    user = get_object_or_404(session, models.User, "external_id", username_from_token)
    return serializers.UserResponse(user=user)


@router.post(
    "/users/forgot-password",
)
def forgot_password(
    user: models.BasicUser, client: CognitoClient = Depends(dependencies.get_cognito_client)
) -> serializers.ResponseBase:
    """
    Initiate the process of resetting a user's password.

    This endpoint initiates the process of resetting a user's password.
    It sends an email to the user with a reset link that they can use to set a new password.

    :param user: The user information containing the username or email address of the user.
    :return: The response indicating that an email with a reset link was sent to the user.
    """
    detail = "An email with a reset link was sent to end user"
    try:
        client.reset_password(user.username)
    except Exception:
        logger.exception("Error resetting password")

    # always return 200 to avoid user enumeration
    return serializers.ResponseBase(detail=detail)


@router.get(
    "/users/{user_id}",
    tags=["users"],
)
async def get_user(user_id: int, session: Session = Depends(get_db)) -> models.User:
    """
    Retrieve information about a user.

    This endpoint retrieves information about a user based on their user_id.

    :param user_id: The ID of the user.
    :return: The user information.
    :raises HTTPException 404: If the user is not found.
    """
    return get_object_or_404(session, models.User, "id", user_id)


@router.get(
    "/users",
    tags=["users"],
)
async def get_all_users(
    page: int = Query(0, ge=0),
    page_size: int = Query(10, gt=0),
    sort_field: str = Query("created_at"),
    sort_order: SortOrder = Query("asc"),
    admin: models.User = Depends(dependencies.get_admin_user),
    session: Session = Depends(get_db),
) -> serializers.UserListResponse:
    """
    Retrieve a list of users.

    This endpoint retrieves a list of users, paginated and sorted based on the provided parameters.

    :param page: The page number (0-based) to retrieve.
    :param page_size: The number of users to retrieve per page.
    :param sort_field: The field to sort the users by. Defaults to "created_at".
    :param sort_order: The sort order. Must be either "asc" or "desc". Defaults to "asc".
    :return: The paginated and sorted list of users.
    """
    list_query = (
        session.query(models.User)
        .outerjoin(models.Lender)
        .options(joinedload(models.User.lender))
        .order_by(get_order_by(sort_field, sort_order, model=models.User), models.User.id)
    )

    total_count = list_query.count()

    users = list_query.offset(page * page_size).limit(page_size).all()

    return serializers.UserListResponse(
        items=users,
        count=total_count,
        page=page,
        page_size=page_size,
    )


@router.put(
    "/users/{id}",
    tags=["users"],
    response_model=models.UserWithLender,
)
async def update_user(
    id: int,
    user: models.User,
    admin: models.User = Depends(dependencies.get_admin_user),
    session: Session = Depends(get_db),
) -> models.User:
    """
    Update a user's information.

    This endpoint updates the information of a specific user identified by the provided ID.

    :param id: The ID of the user to update.
    :param user: The updated user information.
    :return: The updated user information.
    """
    # Rename the query parameter.
    payload = user

    with rollback_on_error(session):
        try:
            db_user = get_object_or_404(session, models.User, "id", id)
            db_user = db_user.update(session, **jsonable_encoder(payload, exclude_unset=True))

            return commit_and_refresh(session, db_user)
        except IntegrityError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="User already exists",
            )
