from functools import lru_cache
from typing import Annotated

import sentry_sdk
from fastapi import Depends, FastAPI

from .core.settings import Settings
from .routers import users

sentry_sdk.init(
    dsn="https://37290b3456f744d889b80c59136c6f5d@o288126.ingest.sentry.io/4505195811766272",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production,
    traces_sample_rate=1.0,
)

app = FastAPI()
app.include_router(users.router)


@lru_cache()
def get_settings():
    return Settings()


@app.get("/")
def read_root():
    return {"Title": "Credence backend"}


@app.api_route("/info")
async def info(settings: Annotated[Settings, Depends(get_settings)]):
    return {"Title": "Credence backend", "version": settings.version}


@app.get("/sentry-debug")
async def trigger_error():
    division_by_zero = 1 / 0
    return division_by_zero
