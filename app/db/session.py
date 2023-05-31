from typing import Generator  # new

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.settings import app_settings

SQLALCHEMY_DATABASE_URL = app_settings.db_url
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:  # new
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()
