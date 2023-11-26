from functools import wraps

from fastapi import HTTPException, status

from app.models import User


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
            user = User.first_by(session, "external_id", current_user)

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
