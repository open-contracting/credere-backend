from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app import auth, aws, dependencies, mail, models, parsers, serializers, util
from app.db import get_db, rollback_on_error
from app.i18n import _
from app.settings import app_settings
from app.util import SortOrder, get_object_or_404

router = APIRouter()


@router.post(
    "/users",
    tags=[util.Tags.users],
)
async def create_user(
    payload: models.UserBase,
    session: Annotated[Session, Depends(get_db)],
    client: Annotated[aws.Client, Depends(dependencies.get_aws_client)],
    admin: Annotated[models.User, Depends(dependencies.get_admin_user)],
) -> models.User:
    """
    Create a new user in Cognito.

    Email the user a temporary password.

    Accessible only to users with the OCP role.
    """
    with rollback_on_error(session):
        try:
            temporary_password = client.generate_password()

            # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cognito-idp/client/admin_create_user.html
            response = client.cognito.admin_create_user(
                UserPoolId=app_settings.cognito_pool_id,
                Username=payload.email,
                TemporaryPassword=temporary_password,
                MessageAction="SUPPRESS",  # do not send user invitation messages
                UserAttributes=[{"Name": "email", "Value": payload.email}],
            )

            user = models.User.create(session, **payload.model_dump())

            user.external_id = response["User"]["Username"]

            session.commit()

            mail.send_new_user(
                client.ses, name=payload.name, username=payload.email, temporary_password=temporary_password
            )
        except (client.cognito.exceptions.UsernameExistsException, IntegrityError):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_("User with that email already exists"),
            ) from None
        return user


@router.put(
    "/users/change-password",
    tags=[util.Tags.authentication],
)
def change_password(
    payload: parsers.BasicUser,
    client: Annotated[aws.Client, Depends(dependencies.get_aws_client)],
) -> serializers.ChangePasswordResponse | serializers.ResponseBase:
    """
    Change user password.

    This endpoint allows users to change their password. It initiates the password change process
    and handles different scenarios such as new password requirement, MFA setup, and error handling.
    """
    # This endpoint is only called for new users, to replace the generated password.
    initiate_response = client.initiate_auth(payload.username, payload.temp_password)
    if initiate_response["ChallengeName"] == "NEW_PASSWORD_REQUIRED":
        respond_response = client.respond_to_auth_challenge(
            username=payload.username,
            session=initiate_response["Session"],
            challenge_name="NEW_PASSWORD_REQUIRED",
            new_password=payload.password,
        )

    # Verify the user's email.
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cognito-idp/client/admin_update_user_attributes.html
    client.cognito.admin_update_user_attributes(
        UserPoolId=app_settings.cognito_pool_id,
        Username=payload.username,
        UserAttributes=[{"Name": "email_verified", "Value": "true"}],
    )

    if "ChallengeName" in respond_response and respond_response["ChallengeName"] == "MFA_SETUP":
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cognito-idp/client/associate_software_token.html
        associate_response = client.cognito.associate_software_token(Session=respond_response["Session"])

        return serializers.ChangePasswordResponse(
            detail=_("Password changed with MFA setup required"),
            secret_code=associate_response["SecretCode"],
            session=associate_response["Session"],
            username=payload.username,
        )

    return serializers.ResponseBase(detail=_("Password changed"))


@router.put(
    "/users/setup-mfa",
    tags=[util.Tags.authentication],
)
def setup_mfa(
    payload: parsers.SetupMFA,
    client: Annotated[aws.Client, Depends(dependencies.get_aws_client)],
) -> serializers.ResponseBase:
    """Set up multi-factor authentication (MFA) for the user."""
    try:
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cognito-idp/client/verify_software_token.html
        client.cognito.verify_software_token(Session=payload.session, UserCode=payload.temp_password)
    except client.cognito.exceptions.NotAuthorizedException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_("Invalid session for the user, session is expired"),
        ) from None
    except client.cognito.exceptions.EnableSoftwareTokenMFAException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_("Invalid MFA code"),
        ) from None

    return serializers.ResponseBase(detail=_("MFA configured successfully"))


@router.post(
    "/users/login",
    tags=[util.Tags.authentication],
)
def login(
    payload: parsers.BasicUser,
    client: Annotated[aws.Client, Depends(dependencies.get_aws_client)],
    session: Annotated[Session, Depends(get_db)],
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
    user = models.User.first_by(session, "email", payload.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,  # prevent user enumeration
            detail=_("Invalid username or password"),
        )

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
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=_("Missing MFA challenge"),
            )
    # The user failed to sign in ("Incorrect username or password", etc.).
    except client.cognito.exceptions.NotAuthorizedException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_("Invalid username or password"),
        ) from None
    except client.cognito.exceptions.CodeMismatchException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_("Invalid MFA code"),
        ) from None

    return serializers.LoginResponse(
        user=user,
        access_token=mfa_login_response["AuthenticationResult"]["AccessToken"],
        refresh_token=mfa_login_response["AuthenticationResult"]["RefreshToken"],
    )


@router.get(
    "/users/logout",
    tags=[util.Tags.authentication],
)
async def logout(
    request: Request,
    client: Annotated[aws.Client, Depends(dependencies.get_aws_client)],
) -> serializers.ResponseBase:
    """Logout the user from all devices in Cognito."""
    try:
        # get_auth_credentials
        credentials = await auth.JWTAuthorization()(request)
        # get_current_user
        username = credentials.claims["username"]
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cognito-idp/client/admin_user_global_sign_out.html
        client.cognito.admin_user_global_sign_out(UserPoolId=app_settings.cognito_pool_id, Username=username)
    # The user is not signed in.
    except (HTTPException, KeyError):
        pass

    return serializers.ResponseBase(detail=_("User logged out successfully"))


@router.get(
    "/users/me",
    tags=[util.Tags.authentication],
)
def me(
    username_from_token: Annotated[str, Depends(dependencies.get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> serializers.UserResponse:
    """
    Get the details of the currently authenticated user.

    This endpoint retrieves the details of the currently authenticated user.
    It uses the username extracted from the JWT token to query the database
    and retrieve the user details.
    """
    user = get_object_or_404(session, models.User, "external_id", username_from_token)
    return serializers.UserResponse(user=user)


@router.post(
    "/users/forgot-password",
    tags=[util.Tags.authentication],
)
def forgot_password(
    payload: parsers.ResetPassword,
    client: Annotated[aws.Client, Depends(dependencies.get_aws_client)],
) -> serializers.ResponseBase:
    """
    Initiate the process of resetting a user's password.

    Email the user a temporary password and a reset link.
    """
    temporary_password = client.generate_password()

    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cognito-idp/client/admin_set_user_password.html
    client.cognito.admin_set_user_password(
        UserPoolId=app_settings.cognito_pool_id,
        Username=payload.username,
        Password=temporary_password,
        Permanent=False,
    )

    mail.send_reset_password(client.ses, username=payload.username, temporary_password=temporary_password)

    # always return 200 to avoid user enumeration
    return serializers.ResponseBase(detail=_("An email with a reset link was sent to end user"))


@router.get(
    "/users/{user_id}",
    tags=[util.Tags.users],
)
async def get_user(
    user_id: int,
    admin: Annotated[models.User, Depends(dependencies.get_admin_user)],
    session: Annotated[Session, Depends(get_db)],
) -> models.User:
    """
    Retrieve information about a user.

    This endpoint retrieves information about a user based on their user_id.
    """
    return get_object_or_404(session, models.User, "id", user_id)


@router.get(
    "/users",
    tags=[util.Tags.users],
)
async def get_all_users(
    admin: Annotated[models.User, Depends(dependencies.get_admin_user)],
    session: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=0)] = 0,
    page_size: Annotated[int, Query(gt=0)] = 10,
    sort_field: Annotated[str, Query()] = "created_at",
    sort_order: Annotated[SortOrder, Query()] = SortOrder.ASC,
) -> serializers.UserListResponse:
    """
    Retrieve a list of users.

    This endpoint retrieves a list of users, paginated and sorted based on the provided parameters.
    """
    list_query = (
        session.query(models.User)
        .outerjoin(models.Lender)
        .options(joinedload(models.User.lender))
        .order_by(models.get_order_by(sort_field, sort_order, model=models.User), models.User.id)
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
    "/users/{user_id}",
    tags=[util.Tags.users],
    response_model=models.UserWithLender,
)
async def update_user(
    user_id: int,
    payload: models.User,
    admin: Annotated[models.User, Depends(dependencies.get_admin_user)],
    session: Annotated[Session, Depends(get_db)],
) -> models.User:
    """
    Update a user's information.

    This endpoint updates the information of a specific user identified by the provided ID.
    """
    with rollback_on_error(session):
        try:
            user = get_object_or_404(session, models.User, "id", user_id)
            user = user.update(session, **jsonable_encoder(payload, exclude_unset=True))

            session.commit()
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_("User with that email already exists"),
            ) from None
        return user
