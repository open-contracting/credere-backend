from functools import wraps
from typing import Dict, List, Optional

import requests
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt
from jose.utils import base64url_decode
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.settings import app_settings
from app.schema.core import User

from ..db.session import get_db

JWK = Dict[str, str]


class JWKS(BaseModel):
    keys: List[JWK]


class JWTAuthorizationCredentials(BaseModel):
    jwt_token: str
    header: Dict[str, str]
    claims: Dict[str, str]
    signature: str
    message: str


class verifyTokeClass(HTTPBearer):
    """
    An extension of HTTPBearer authentication to verify JWT (JSON Web Tokens) with public keys.
    This class loads and keeps track of public keys from an external source and verifies incoming tokens.

    :param auto_error: If set to True, automatic error responses will be sent when request authentication fails.
                       Default is True.
    :type auto_error: bool
    """

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.kid_to_jwk = None

    def load_keys(self):
        if self.kid_to_jwk is None:
            jwks = get_public_keys()
            self.kid_to_jwk = {jwk["kid"]: jwk for jwk in jwks.keys}

    def verify_jwk_token(self, jwt_credentials: JWTAuthorizationCredentials) -> bool:
        """
        Verifies the provided JWT credentials with the loaded public keys.

        :param jwt_credentials: JWT credentials extracted from the request.
        :type jwt_credentials: JWTAuthorizationCredentials
        :return: Returns True if the token is verified, False otherwise.
        :rtype: bool
        """
        self.load_keys()
        try:
            public_key = self.kid_to_jwk[jwt_credentials.header["kid"]]
        except KeyError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="JWK public key not found")

        key = jwk.construct(public_key)
        decoded_signature = base64url_decode(jwt_credentials.signature.encode())

        return key.verify(jwt_credentials.message.encode(), decoded_signature)

    async def __call__(self, request: Request) -> Optional[JWTAuthorizationCredentials]:
        """
        Authenticate and verify the provided JWT token in the request.

        :param request: Incoming request instance.
        :type request: Request
        :return: JWT credentials if the token is verified.
        :rtype: Optional[JWTAuthorizationCredentials]
        """
        self.load_keys()
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)

        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Wrong authentication method",
                )

            jwt_token = credentials.credentials

            message, signature = jwt_token.rsplit(".", 1)

            try:
                jwt_credentials = JWTAuthorizationCredentials(
                    jwt_token=jwt_token,
                    header=jwt.get_unverified_header(jwt_token),
                    claims=jwt.get_unverified_claims(jwt_token),
                    signature=signature,
                    message=message,
                )
            except JWTError:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="JWK invalid")

            if not self.verify_jwk_token(jwt_credentials):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="JWK invalid")

            return jwt_credentials
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authenticated",
            )


JsonPublicKeys = None


def get_public_keys():
    """
    Retrieves the public keys from the well-known JWKS (JSON Web Key Set) endpoint of AWS Cognito.

    The function caches the fetched keys in a global variable `JsonPublicKeys` to avoid repetitive calls
    to the endpoint.

    :return: The parsed JWKS, an object which holds a list of keys.
    :rtype: JWKS
    """
    global JsonPublicKeys
    if JsonPublicKeys is None:
        JsonPublicKeys = JWKS.parse_obj(
            requests.get(
                f"https://cognito-idp.{app_settings.aws_region}.amazonaws.com/"
                f"{app_settings.cognito_pool_id}/.well-known/jwks.json"
            ).json()
        )
    return JsonPublicKeys


async def get_auth_credentials(request: Request):
    return await verifyTokeClass().__call__(request)


async def get_current_user(
    credentials: JWTAuthorizationCredentials = Depends(get_auth_credentials),
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
    credentials: JWTAuthorizationCredentials = Depends(get_auth_credentials),
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
    :rtype: User
    """
    try:
        return User.first_by(session, "external_id", credentials.claims["username"])
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
