from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import applications, downloads, guest, lenders, statistics, users
from app.settings import app_settings

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", app_settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(applications.router)
app.include_router(guest.applications.router)
app.include_router(guest.emails.router)
app.include_router(downloads.router)
app.include_router(lenders.router)
app.include_router(statistics.router)
