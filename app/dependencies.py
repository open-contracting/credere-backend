from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Generator

from fastapi import Depends, Form, HTTPException, Request, status
from sqlalchemy.orm import Session, defaultload, joinedload

from app import auth, models, parsers, util
from app.aws import cognito_client
from app.db import get_db

OCP_CAN_MODIFY = (
    models.ApplicationStatus.PENDING,
    models.ApplicationStatus.ACCEPTED,
    models.ApplicationStatus.SUBMITTED,
    models.ApplicationStatus.STARTED,
    models.ApplicationStatus.INFORMATION_REQUESTED,
)


class ApplicationScope(Enum):
    UNEXPIRED = "UNEXPIRED"


def get_cognito_client() -> Generator:  # new
    yield cognito_client


async def get_auth_credentials(request: Request):
    return await auth.verifyTokeClass().__call__(request)


async def get_current_user(credentials: auth.JWTAuthorizationCredentials = Depends(get_auth_credentials)) -> str:
    """
    Extracts the username of the current user from the provided JWT credentials.

    :param credentials: JWT credentials provided by the user. Defaults to Depends(get_auth_credentials).
    :type credentials: JWTAuthorizationCredentials
    :raises HTTPException: If the username key is missing in the JWT claims.
    :return: The username of the current user.
    :rtype: str
    """
    try:
        return credentials.claims["username"]
    except KeyError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Username missing")


async def get_user(username: str = Depends(get_current_user), session: Session = Depends(get_db)) -> str:
    """
    Retrieves the user from the database using the username extracted from the provided JWT credentials.

    :param credentials: JWT credentials provided by the user. Defaults to Depends(get_auth_credentials).
    :type credentials: JWTAuthorizationCredentials
    :param session: Database session to execute the query. Defaults to Depends(get_db).
    :type session: Session
    :raises HTTPException: If the user does not exist in the database.
    :return: The user object retrieved from the database.
    :rtype: models.User
    """
    return models.User.first_by(session, "external_id", username)


def OCP_only():
    """
    A decorator to check if the user is an OCP user.
    Raises HTTPException if the user is not authenticated or not an OCP user.

    :param setUser: If True, the user is passed as a keyword argument to the decorated function.
    :type setUser: bool, optional

    :return: The decorator function.
    :rtype: function

    :raises HTTPException: If the user is not authenticated or not an OCP user.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials",
                )
            session = kwargs.get("session")

            # Retrieve the user from the session using external_id
            user = models.User.first_by(session, "external_id", current_user)

            # Check if the user has the required permission
            if user and user.is_OCP():
                return await func(*args, **kwargs)
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Insufficient permissions",
                )

        return wrapper

    return decorator


def raise_if_unauthorized(
    application: models.Application,
    user: models.User | None = None,
    *,
    roles: tuple[models.UserType] = (),
    scopes: tuple[ApplicationScope] = (),
    statuses: tuple[models.ApplicationStatus] = (),
):
    if roles:
        for role in roles:
            match role:
                case models.UserType.OCP:
                    if user.is_OCP():
                        break
                case models.UserType.FI:
                    if user.lender_id == application.lender_id:
                        break
                case _:
                    raise NotImplementedError
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not authorized")

    if ApplicationScope.UNEXPIRED in scopes:
        expired_at = application.expired_at
        if expired_at and expired_at < datetime.now(expired_at.tzinfo):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Application expired")

    if statuses:
        if application.status not in statuses:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Application status should not be {application.status.name}",
            )


def get_publication_as_user(id: int, session: Session = Depends(get_db)) -> models.Application:
    application = (
        models.Application.filter_by(session, "id", id)
        .options(joinedload(models.Application.borrower), joinedload(models.Application.award))
        .first()
    )
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    return application


def get_scoped_publication_as_user(
    *, roles: tuple[models.UserType] = (), statuses: tuple[models.ApplicationStatus] = ()
):
    def inner(
        application: models.Application = Depends(get_publication_as_user), user: models.User = Depends(get_user)
    ) -> models.Application:
        raise_if_unauthorized(application, user, roles=roles, statuses=statuses)
        return application

    return inner


def _get_publication_as_guest_via_uuid(session: Session, uuid: str) -> models.Application:
    """
    Retrieve an application by its UUID from the database.

    This function queries the database to find an application that matches the given UUID.
    It raises an HTTPException if no such application is found or if the application's status is LAPSED.
    """
    application = (
        models.Application.filter_by(session, "uuid", uuid)
        .options(
            defaultload(models.Application.borrower),
            defaultload(models.Application.award),
            defaultload(models.Application.borrower_documents),
        )
        .first()
    )
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    if application.status == models.ApplicationStatus.LAPSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=util.ERROR_CODES.APPLICATION_LAPSED.value,
        )

    return application


def _get_scoped_publication_as_guest_inner(
    depends, scopes: tuple[ApplicationScope] = (), statuses: tuple[models.ApplicationStatus] = ()
):
    def inner(application: models.Application = Depends(depends)) -> models.Application:
        raise_if_unauthorized(application, scopes=scopes, statuses=statuses)
        return application

    return inner


def get_publication_as_guest_via_payload(
    payload: parsers.ApplicationBase, session: Session = Depends(get_db)
) -> models.Application:
    return _get_publication_as_guest_via_uuid(session, payload.uuid)


def get_publication_as_guest_via_uuid(uuid: str, session: Session = Depends(get_db)) -> models.Application:
    return _get_publication_as_guest_via_uuid(session, uuid)


def get_publication_as_guest_via_form(uuid: str = Form(...), session: Session = Depends(get_db)) -> models.Application:
    return _get_publication_as_guest_via_uuid(session, uuid)


def get_scoped_publication_as_guest_via_payload(
    *, scopes: tuple[ApplicationScope] = (), statuses: tuple[models.ApplicationStatus] = ()
):
    return _get_scoped_publication_as_guest_inner(get_publication_as_guest_via_payload, scopes, statuses)


def get_scoped_publication_as_guest_via_uuid(
    *, scopes: tuple[ApplicationScope] = (), statuses: tuple[models.ApplicationStatus] = ()
):
    return _get_scoped_publication_as_guest_inner(get_publication_as_guest_via_uuid, scopes, statuses)


def get_scoped_publication_as_guest_via_form(
    *, scopes: tuple[ApplicationScope] = (), statuses: tuple[models.ApplicationStatus] = ()
):
    return _get_scoped_publication_as_guest_inner(get_publication_as_guest_via_form, scopes, statuses)
