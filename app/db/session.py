from contextlib import contextmanager
from typing import Generator  # new

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from app.core.settings import app_settings

SessionLocal = None
if app_settings.database_url:
    engine = create_engine(app_settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def transaction_session(db: Session):
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_db() -> Generator:  # new
    try:
        db = None
        if SessionLocal:
            db = SessionLocal()

        yield db
    finally:
        if db:
            db.close()
