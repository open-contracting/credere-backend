import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.settings import Settings
from .routers import users

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


@app.get("/")
def read_root():
    return {"Title": "Credence backend"}


@app.api_route("/info")
async def info():
    return {"Title": "Credence backend", "version": Settings().version}
