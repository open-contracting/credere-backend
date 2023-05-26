import sentry_sdk
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.settings import Settings
from .routers import users
from .utils.auth_get_cognito_public_keys import JsonPublicKeys, get_current_user
from .utils.verify_token import verifyTokeClass

if Settings().sentry_dsn:
    sentry_sdk.init(
        dsn=Settings().sentry_dsn,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production,
        traces_sample_rate=1.0,
    )

app = FastAPI()

# Configure CORS settings
origins = [
    Settings().frontend_url
    # Add more allowed origins as needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
authorizedCredentials = verifyTokeClass(JsonPublicKeys)


@app.get("/")
def read_root():
    return {"Title": "Credence backend"}


@app.api_route("/info")
async def info():
    return {"Title": "Credence backend", "version": Settings().version}


@app.get("/secure-endpoint-example", dependencies=[Depends(authorizedCredentials)])
def example_of_secure_endpoint():
    return {"Congrats,you were autorized to see this endpoint"}


@app.get(
    "/secure-endpoint-example-username-extraction",
    dependencies=[Depends(authorizedCredentials)],
)
def example_of_secure_endpoint_with_username(
    usernameFromToken: str = Depends(get_current_user),
):
    print(usernameFromToken)
    return {"Congrats" + usernameFromToken + " you were autorized to see this endpoint"}
