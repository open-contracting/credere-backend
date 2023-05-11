from fastapi import APIRouter
from ..schema.user_tables.users import User
from datetime import datetime
from sqlmodel import Session
from ..db.database import engine

router = APIRouter()
session = Session(bind=engine)

user = User(
    id=1,
    type="customer",
    email="jane@example.com",
    external_id="12345",
    fl_id=10,
    created_at=datetime.now(),
)


@router.get("/users/", tags=["users"], response_model=User)
async def read_user():
    return user
