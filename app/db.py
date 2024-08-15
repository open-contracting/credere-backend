import traceback
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import models
from app.exceptions import SkippedAwardError
from app.settings import app_settings

# https://docs.sqlalchemy.org/en/20/orm/session_basics.html#using-a-sessionmaker
engine = create_engine(app_settings.test_database_url if app_settings.test_database_url else app_settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def rollback_on_error(session: Session) -> Generator[None, None, None]:
    try:
        yield
    except Exception:
        session.rollback()
        raise


@contextmanager
def handle_skipped_award(session: Session, msg: str) -> Generator[None, None, None]:
    try:
        yield
    except SkippedAwardError as e:
        session.rollback()
        models.EventLog.create(
            session,
            category=e.category,
            message=f"{msg}: {e.message}",
            url=e.url,
            data=e.data,
            traceback=traceback.format_exc(),
        )
        session.commit()
    except Exception:
        session.rollback()
        raise


# This is a FastAPI dependency.
def get_db() -> Generator[Session, None, None]:
    """
    Generator function to get a new database session. Yields a database session instance and closes the session after
    it is used.

    :return: The database session instance.
    """
    with SessionLocal() as session:
        yield session
