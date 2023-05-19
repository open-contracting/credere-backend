from fastapi import FastAPI

from .core.settings import Settings
from .routers import users

app = FastAPI()
app.include_router(users.router)


@app.get("/")
def read_root():
    return {"Title": "Credence backend"}


@app.api_route("/info")
async def info():
    return {"Title": "Credence backend", "version": Settings().version}
