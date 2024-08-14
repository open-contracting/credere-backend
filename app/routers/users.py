import logging

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app import aws, dependencies, mail, models, serializers
from app.db import get_db, rollback_on_error
from app.settings import app_settings
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
    client: aws.Client = Depends(dependencies.get_aws_client),
    admin: models.User = Depends(dependencies.get_admin_user),
) -> models.User:
    """
    Create a new user in AWS Cognito.

    Email the user a temporary password.

    Accessible only to users with the OCP role.

    :param payload: The user data for creating the new user.
    :return: The created user.
    """
    with rollback_on_error(session):
        try:
            user = models.User.create(session, **payload.model_dump())

            temporary_password = client.generate_password()

            response = client.cognito.admin_create_user(
                UserPoolId=app_settings.cognito_pool_id,
                Username=payload.email,
                TemporaryPassword=temporary_password,
                MessageAction="SUPPRESS",
                UserAttributes=[{"Name": "email", "Value": payload.email}],
            )

            mail.send_mail_to_new_user(client.ses, payload.name, payload.email, temporary_password)

            user.external_id = response["User"]["Username"]

            return commit_and_refresh(session, user)
        except (client.cognito.exceptions.UsernameExistsException, IntegrityError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Username already exists",
            )


@router.put(
    "/users/change-password",
)
def change_password(
    user: models.BasicUser,
    client: aws.Client = Depends(dependencies.get_aws_client),
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
        # This endpoint is only called for new users, to replace the generated password.
        response = client.initiate_auth(user.username, user.temp_password)
        if response["ChallengeName"] == "NEW_PASSWORD_REQUIRED":
            response = client.respond_to_auth_challenge(
                username=user.username,
                session=response["Session"],
                challenge_name="NEW_PASSWORD_REQUIRED",
                new_password=user.password,
            )

        # Verify the user's email.
        client.cognito.admin_update_user_attributes(
            UserPoolId=app_settings.cognito_pool_id,
            Username=user.username,
            UserAttributes=[
                {"Name": "email_verified", "Value": "true"},
            ],
        )

        if "ChallengeName" in response and response["ChallengeName"] == "MFA_SETUP":
            associate_response = client.cognito.associate_software_token(Session=response["Session"])

            return serializers.ChangePasswordResponse(
                detail="Password changed with MFA setup required",
                secret_code=associate_response["SecretCode"],
                session=associate_response["Session"],
                username=user.username,
            )
    except ClientError as e:
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

    return serializers.ResponseBase(detail="Password changed")


@router.put(
    "/users/setup-mfa",
)
def setup_mfa(
    setup_mfa: models.SetupMFA,
    client: aws.Client = Depends(dependencies.get_aws_client),
) -> serializers.ResponseBase:
    """
    Set up multi-factor authentication (MFA) for the user.

    This endpoint allows users to set up MFA using a software token. It verifies the software
    token with the provided secret, session, and temporary password.

    :param setup_mfa: The user data including the secret code, session, and temporary password.
    :param response: The response object used to modify the response headers (automatically injected).
    :return: The response indicating successful MFA setup or an error response.
    """
    try:
        client.cognito.verify_software_token(
            AccessToken=setup_mfa.secret, Session=setup_mfa.session, UserCode=setup_mfa.temp_password
        )
    except ClientError as e:
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

    return serializers.ResponseBase(detail="MFA configured successfully")


@router.post(
    "/users/login",
)
def login(
    payload: models.BasicUser,
    client: aws.Client = Depends(dependencies.get_aws_client),
    session: Session = Depends(get_db),
) -> serializers.LoginResponse:
    """
    Authenticate the user with Multi-Factor Authentication (MFA) and generate access and refresh tokens.

    This endpoint handles user login and authentication with MFA. It initiates the authentication
    process using the provided username and password. If the authentication process requires MFA,
    it responds to the MFA challenge by providing the MFA code. If the authentication is successful,
    it returns the user information along with the generated access and refresh tokens.

    :param payload: The user data including the username, password, and MFA code.
    :return: The response containing the user information and tokens if the login is successful.
    """
    user = get_object_or_404(session, models.User, "email", payload.username)

    try:
        response = client.initiate_auth(payload.username, payload.password)

        if "ChallengeName" in response:
            mfa_login_response = client.respond_to_auth_challenge(
                username=payload.username,
                session=response["Session"],
                challenge_name=response["ChallengeName"],
                mfa_code=payload.temp_password,
            )
        else:
            raise NotImplementedError
    except ClientError as e:
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

    return serializers.LoginResponse(
        user=user,
        access_token=mfa_login_response["access_token"],
        refresh_token=mfa_login_response["refresh_token"],
    )


@router.get(
    "/users/logout",
)
def logout(
    authorization: str | None = Header(None),
    client: aws.Client = Depends(dependencies.get_aws_client),
) -> serializers.ResponseBase:
    """
    Logout the user from all devices in AWS Cognito.

    :param authorization: The Authorization header, like "Bearer ACCESS_TOKEN".
    :return: The response indicating successful logout.
    """

    # The Authorization header is not set if the user is already logged out.
    if authorization is not None:
        try:
            response = client.cognito.get_user(AccessToken=authorization.split(" ")[1])
            # "If `username` isn’t an alias attribute in your user pool, this value must be the `sub` of a local user
            # or the username of a user from a third-party IdP."
            # https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-attributes.html
            sub = next(attribute["Value"] for attribute in response["UserAttributes"] if attribute["Name"] == "sub")
            # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cognito-idp/client/admin_user_global_sign_out.html
            client.cognito.admin_user_global_sign_out(UserPoolId=app_settings.cognito_pool_id, Username=sub)
        # The user is not signed in ("Access Token has expired", "Invalid token", etc.).
        except client.cognito.exceptions.NotAuthorizedException:
            pass
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
    user: models.BasicUser, client: aws.Client = Depends(dependencies.get_aws_client)
) -> serializers.ResponseBase:
    """
    Initiate the process of resetting a user's password.

    Email the user a temporary password and a reset link.

    :param user: The user information containing the username or email address of the user.
    :return: The response indicating that an email with a reset link was sent to the user.
    """
    detail = "An email with a reset link was sent to end user"
    try:
        temporary_password = client.generate_password()

        client.cognito.admin_set_user_password(
            UserPoolId=app_settings.cognito_pool_id,
            Username=user.username,
            Password=temporary_password,
            Permanent=False,
        )

        mail.send_mail_to_reset_password(client.ses, user.username, temporary_password)
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

    users = list_query.limit(page_size).offset(page * page_size).all()

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
    payload: models.User,
    admin: models.User = Depends(dependencies.get_admin_user),
    session: Session = Depends(get_db),
) -> models.User:
    """
    Update a user's information.

    This endpoint updates the information of a specific user identified by the provided ID.

    :param id: The ID of the user to update.
    :param payload: The updated user information.
    :return: The updated user information.
    """
    with rollback_on_error(session):
        try:
            user = get_object_or_404(session, models.User, "id", id)
            user = user.update(session, **jsonable_encoder(payload, exclude_unset=True))

            return commit_and_refresh(session, user)
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="User already exists",
            )
