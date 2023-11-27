from functools import wraps
from typing import Generator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import auth, models
from app.aws import cognito_client
from app.db import get_db


def get_cognito_client() -> Generator:  # new
    yield cognito_client


async def get_auth_credentials(request: Request):
    return await auth.verifyTokeClass().__call__(request)


async def get_current_user(
    credentials: auth.JWTAuthorizationCredentials = Depends(get_auth_credentials),
) -> str:
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


async def get_user(
    credentials: auth.JWTAuthorizationCredentials = Depends(get_auth_credentials),
    session: Session = Depends(get_db),
) -> str:
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
    try:
        return models.User.first_by(session, "external_id", credentials.claims["username"])
    except KeyError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not found")


def OCP_only(setUser=False):
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
                if setUser:
                    kwargs["user"] = user  # Pass the user as a keyword argument
                return await func(*args, **kwargs)
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Insufficient permissions",
                )

        return wrapper

    return decorator
