import requests
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt
from jose.utils import base64url_decode
from pydantic import BaseModel

from app.settings import app_settings

JWK = dict[str, str]


class JWKS(BaseModel):
    keys: list[JWK]


class JWTAuthorizationCredentials(BaseModel):
    jwt_token: str
    header: dict[str, str]
    claims: dict[str, str]
    signature: str
    message: str


class verifyTokeClass(HTTPBearer):
    """
    An extension of HTTPBearer authentication to verify JWT (JSON Web Tokens) with public keys.
    This class loads and keeps track of public keys from an external source and verifies incoming tokens.

    :param auto_error: If set to True, automatic error responses will be sent when request authentication fails.
                       Default is True.
    """

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.kid_to_jwk = None

    def load_keys(self):
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
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="JWK public key not found")

        key = jwk.construct(public_key)
        decoded_signature = base64url_decode(jwt_credentials.signature.encode())

        return key.verify(jwt_credentials.message.encode(), decoded_signature)

    async def __call__(self, request: Request) -> JWTAuthorizationCredentials | None:
        """
        Authenticate and verify the provided JWT token in the request.

        :param request: Incoming request instance.
        :return: JWT credentials if the token is verified.
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


def _get_public_keys() -> JWKS:
    """
    Retrieves the public keys from the well-known JWKS (JSON Web Key Set) endpoint of AWS Cognito.

    The function caches the fetched keys in a global variable `JsonPublicKeys` to avoid repetitive calls
    to the endpoint.

    :return: The parsed JWKS, an object which holds a list of keys.
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
