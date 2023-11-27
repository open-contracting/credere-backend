import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.exceptions import SkippedAwardError
from app.settings import app_settings

logger = logging.getLogger(__name__)

SessionLocal = None
if app_settings.database_url:
    engine = create_engine(app_settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
if app_settings.test_database_url:
    engine = create_engine(app_settings.test_database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def transaction_session(db: Session):
    """
    Context manager for database transactions. It takes a Session instance, commits the transaction if it is successful, # noqa
    and rolls back the transaction if any exception is raised.

    :param db: The database session where the transaction is to be performed.
    :raises Exception: Any exception that occurs during the transaction.
    :yield: The same database session, for use in with-statement.
    """
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise


@contextmanager
def transaction_session_logger(session: Session, msg: str, *args):
    try:
        yield session
        session.commit()
    # Don't display tracebacks in emails from cron jobs for anticipated errors.
    except SkippedAwardError as e:
        logger.error(f"{msg}: {e}", *args)
        session.rollback()
    except Exception:
        logger.exception(msg, *args)
        session.rollback()


def get_db() -> Generator:
    """
    Generator function to get a new database session. Yields a database session instance and closes the session after
    it is used.

    :return: The database session instance.
    """
    try:
        db = None
        if SessionLocal:
            db = SessionLocal()

        yield db
    finally:
        if db:
            db.close()
