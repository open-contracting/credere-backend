import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.exceptions import SkippedAwardError
from app.settings import app_settings

logger = logging.getLogger(__name__)

engine = create_engine(app_settings.test_database_url if app_settings.test_database_url else app_settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def rollback_on_error(session: Session) -> Generator[Session, None, None]:
    try:
        yield
    except Exception:
        session.rollback()
        raise


@contextmanager
def transaction_session(session: Session) -> Generator[Session, None, None]:
    """
    Context manager for database transactions. It takes a Session instance, commits the transaction if it is
    successful, and rolls back the transaction if any exception is raised.

    :param session: The database session where the transaction is to be performed.
    :raises Exception: Any exception that occurs during the transaction.
    :yield: The same database session, for use in with-statement.
    """
    try:
        yield
        session.commit()
    except Exception:
        session.rollback()
        raise


@contextmanager
def handle_skipped_award(session: Session, msg: str, *args: str) -> Generator[Session, None, None]:
    try:
        yield
    # Don't display tracebacks in emails from cron jobs for anticipated errors.
    except SkippedAwardError as e:
        # msg can contain %s placeholders.
        logger.error(f"{msg}: {e}", *args)
        session.rollback()
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
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
