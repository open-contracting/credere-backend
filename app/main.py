from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI

from .core.settings import Settings
from .routers import users
from .utils.auth_get_cognito_public_keys import JsonPublicKeys, get_current_user
from .utils.verify_token import verifyTokeClass

app = FastAPI()
app.include_router(users.router)
authorizedCredentials = verifyTokeClass(JsonPublicKeys)


@lru_cache()
def get_settings():
    return Settings()


@app.get("/")
def read_root():
    return {"Title": "Credence backend"}


@app.api_route("/info")
async def info(settings: Annotated[Settings, Depends(get_settings)]):
    return {"Title": "Credence backend", "version": settings.version}


@app.get("/secure-endpoint-example", dependencies=[Depends(authorizedCredentials)])
def example_of_secure_endpoint():
    return {"Congrats,you were autorized to see this endpoint"}


@app.get("/secure-endpoint-example-username-extraction", dependencies=[Depends(authorizedCredentials)])
def example_of_secure_endpoint_with_username(usernameFromToken: str = Depends(get_current_user)):
    print(usernameFromToken)
    return {"Congrats" + usernameFromToken + " you were autorized to see this endpoint"}
