from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import app_settings

from .routers import applications, lenders, users  # isort:skip
from .routers import statistics  # isort:skip


app = FastAPI()

# Configure CORS settings
origins = [
    "http://localhost:3000",
    app_settings.frontend_url,
]  # Add more allowed origins as needed

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(applications.router)
app.include_router(lenders.router)
app.include_router(statistics.router)


@app.get("/")
def read_root():
    return {"Title": "Credere backend"}


@app.api_route("/info")
async def info():
    return {"Title": "Credere backend", "version": app_settings.version}
