from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI
from .core.settings import Settings
from .routers import users

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
