import os

import requests
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from starlette.status import HTTP_403_FORBIDDEN

from .verify_token import JWKS, JWTAuthorizationCredentials, verifyTokeClass

load_dotenv()  # Automatically load environment variables from a '.env' file.

JsonPublicKeys = JWKS.parse_obj(
    requests.get(
        f"https://cognito-idp.{os.environ.get('COGNITO_REGION')}.amazonaws.com/"
        f"{os.environ.get('COGNITO_POOL_ID')}/.well-known/jwks.json"
    ).json()
)

authorizedCredentials = verifyTokeClass(JsonPublicKeys)


async def get_current_user(credentials: JWTAuthorizationCredentials = Depends(authorizedCredentials)) -> str:
    try:
        return credentials.claims["username"]
    except KeyError:
        HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Username missing")
