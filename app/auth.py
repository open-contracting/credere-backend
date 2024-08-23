from typing import Any

import jwt
import requests  # moto intercepts only requests, not httpx: https://github.com/getmoto/moto/issues/4197
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer
from jwt.utils import base64url_decode
from pydantic import BaseModel

from app.i18n import _
from app.settings import app_settings

JWK = dict[str, str]


class JWKS(BaseModel):
    keys: list[JWK]


class JWTAuthorizationCredentials(BaseModel):
    jwt_token: str
    header: dict[str, str]
    claims: dict[str, Any]
    signature: str
    message: str


class JWTAuthorization(HTTPBearer):
    """
    An extension of HTTPBearer authentication to verify JWT (JSON Web Tokens) with public keys.
    This class loads and keeps track of public keys from an external source and verifies incoming tokens.

    :param auto_error: If set to True, automatic error responses will be sent when request authentication fails.
                       Default is True.
    """

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.kid_to_jwk: dict[str, JWK] | None = None

    def load_keys(self) -> None:
        if self.kid_to_jwk is None:
            jwks = _get_public_keys()
            self.kid_to_jwk = {jwk["kid"]: jwk for jwk in jwks.keys}

    def verify_jwk_token(self, jwt_credentials: JWTAuthorizationCredentials) -> bool:
        """
        Verifies the provided JWT credentials with the loaded public keys.

        :param jwt_credentials: JWT credentials extracted from the request.
        :return: Returns True if the token is verified, False otherwise.
        """
        self.load_keys()
        try:
            public_key = self.kid_to_jwk[jwt_credentials.header["kid"]]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_("JWK public key not found"),
            )

        msg = jwt_credentials.message.encode()
        sig = base64url_decode(jwt_credentials.signature.encode())

        obj = jwt.PyJWK(public_key)
        alg_obj = obj.Algorithm
        prepared_key = alg_obj.prepare_key(obj.key)

        return alg_obj.verify(msg, prepared_key, sig)

    async def __call__(self, request: Request) -> JWTAuthorizationCredentials:
        """
        Authenticate and verify the provided JWT token in the request.

        :param request: Incoming request instance.
        :return: JWT credentials if the token is verified.
        """
        self.load_keys()

        if credentials := await super().__call__(request):
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=_("Wrong authentication method"),
                )

            jwt_token = credentials.credentials

            if "." in jwt_token:
                message, signature = jwt_token.rsplit(".", 1)
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=_("JWK invalid"),
                )

            try:
                jwt_credentials = JWTAuthorizationCredentials(
                    jwt_token=jwt_token,
                    header=jwt.get_unverified_header(jwt_token),
                    claims=jwt.decode(jwt_token, options={"verify_signature": False}),
                    signature=signature,
                    message=message,
                )
            except jwt.InvalidTokenError:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=_("JWK invalid"),
                )

            if not self.verify_jwk_token(jwt_credentials):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=_("JWK invalid"),
                )

            return jwt_credentials
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_("Not authenticated"),
            )


public_keys = None


def _get_public_keys() -> JWKS:
    """
    Retrieves the public keys from the well-known JWKS (JSON Web Key Set) endpoint of Cognito.

    The function caches the fetched keys in a global variable `public_keys` to avoid repetitive calls
    to the endpoint.

    :return: The parsed JWKS, an object which holds a list of keys.
    """
    global public_keys
    if public_keys is None:
        public_keys = JWKS.model_validate(
            # https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-verifying-a-jwt.html
            requests.get(
                f"https://cognito-idp.{app_settings.aws_region}.amazonaws.com/"
                f"{app_settings.cognito_pool_id}/.well-known/jwks.json"
            ).json()
        )
    return public_keys
