from datetime import datetime

from fastapi import APIRouter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session

from ..core.settings import Settings
from ..db.database import engine
from ..schema.user_tables.users import ApplicationAction, User

router = APIRouter()
session = Session(bind=engine)

application_action = ApplicationAction(
    type="action_type",
    data={"key1": "value1", "key2": "value2"},
    application_id="application_id_value",
    user_id=123,
    created_at=datetime.now(),
)

user = User(
    id=1,
    type="customer",
    email="jane@example.com",
    external_id="12345",
    fl_id=10,
    created_at=datetime.now(),
)
engine = create_engine(Settings().DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@router.get("/users/", tags=["users"], response_model=User)
async def read_user():
    return user


@router.post("/users/", tags=["users"], response_model=User)
async def create_user(user: User):
    db_user = User(**user.dict())

    db = SessionLocal()
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return user
