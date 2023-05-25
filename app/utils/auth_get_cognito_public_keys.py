import os

import requests
from dotenv import load_dotenv
from fastapi import Depends, HTTPException

from .verify_token import JWKS, JWTAuthorizationCredentials, verifyTokeClass

load_dotenv()

JsonPublicKeys = JWKS.parse_obj(
    requests.get(
        f"https://cognito-idp.{os.environ.get('COGNITO_REGION')}.amazonaws.com/"
        f"{os.environ.get('COGNITO_POOL_ID')}/.well-known/jwks.json"
    ).json()
)

# The section below is for username Extration from code
authorizedCredentials = verifyTokeClass(JsonPublicKeys)


async def get_current_user(credentials: JWTAuthorizationCredentials = Depends(authorizedCredentials)) -> str:
    try:
        return credentials.claims["username"]
    except KeyError:
        HTTPException(status_code=403, detail="Username missing")
