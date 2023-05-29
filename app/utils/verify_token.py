from typing import Dict, List, Optional

import requests
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt
from jose.utils import base64url_decode
from pydantic import BaseModel

from app.core.settings import Settings

settings = Settings()

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
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.kid_to_jwk = None

    def load_keys(self):
        if self.kid_to_jwk is None:
            jwks = get_public_keys()
            self.kid_to_jwk = {jwk["kid"]: jwk for jwk in jwks.keys}

    def verify_jwk_token(self, jwt_credentials: JWTAuthorizationCredentials) -> bool:
        self.load_keys()
        try:
            public_key = self.kid_to_jwk[jwt_credentials.header["kid"]]
        except KeyError:
            raise HTTPException(status_code=403, detail="JWK public key not found")

        key = jwk.construct(public_key)
        decoded_signature = base64url_decode(jwt_credentials.signature.encode())

        return key.verify(jwt_credentials.message.encode(), decoded_signature)

    async def __call__(self, request: Request) -> Optional[JWTAuthorizationCredentials]:
        self.load_keys()
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)

        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=403, detail="Wrong authentication method"
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
                raise HTTPException(status_code=403, detail="JWK invalid")

            if not self.verify_jwk_token(jwt_credentials):
                raise HTTPException(status_code=403, detail="JWK invalid")

            return jwt_credentials


JsonPublicKeys = None


def get_public_keys():
    global JsonPublicKeys
    if JsonPublicKeys is None:
        JsonPublicKeys = JWKS.parse_obj(
            requests.get(
                f"https://cognito-idp.{settings.aws_region}.amazonaws.com/"
                f"{settings.cognito_pool_id}/.well-known/jwks.json"
            ).json()
        )
    return JsonPublicKeys


async def get_auth_credentials(request: Request):
    return await verifyTokeClass().__call__(request)


async def get_current_user(
    credentials: JWTAuthorizationCredentials = Depends(get_auth_credentials),
) -> str:
    try:
        return credentials.claims["username"]
    except KeyError:
        raise HTTPException(status_code=403, detail="Username missing")
