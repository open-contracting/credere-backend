from fastapi import FastAPI, Depends
from .routers import users
from .core.settings import Settings
from functools import lru_cache
from typing import Annotated

app = FastAPI()
app.include_router(users.router)


@lru_cache()
def get_settings():
    return Settings()


@app.get("/")
def read_root():
    return {"Title": "Credence backend"}


@app.get("/info")
async def info(settings: Annotated[Settings, Depends(get_settings)]):
    return {"Title": "Credence backend", "version": settings.version}
