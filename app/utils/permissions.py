from functools import wraps

from fastapi import HTTPException, status

from ..schema.core import User


def OCP_only(setUser=False):
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
            user = session.query(User).filter(User.external_id == current_user).first()

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
