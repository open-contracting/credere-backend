from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.settings import Settings
from .routers import users

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
