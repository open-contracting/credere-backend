import requests
from fastapi import Depends, HTTPException

from app.core.settings import Settings

from .verify_token import JWKS, JWTAuthorizationCredentials, verifyTokeClass

settings = Settings()

JsonPublicKeys = JWKS.parse_obj(
    requests.get(
        f"https://cognito-idp.{settings.aws_region}.amazonaws.com/"
        f"{settings.cognito_pool_id}/.well-known/jwks.json"
    ).json()
)

# The section below is for username Extration from code
authorizedCredentials = verifyTokeClass(JsonPublicKeys)


async def get_current_user(
    credentials: JWTAuthorizationCredentials = Depends(authorizedCredentials),
) -> str:
    try:
        return credentials.claims["username"]
    except KeyError:
        HTTPException(status_code=403, detail="Username missing")
