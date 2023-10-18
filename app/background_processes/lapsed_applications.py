import logging
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.session import get_db, transaction_session_logger
from app.schema.core import ApplicationStatus

from . import application_utils

logger = logging.getLogger(__name__)

get_lapses_applications = application_utils.get_lapsed_applications


def set_lapsed_applications(db_provider: Session = get_db):
    """
    Set applications with lapsed status in the database.

    This function retrieves the lapsed applications from the database and updates their status
    to "LAPSED" and sets the application_lapsed_at timestamp to the current UTC time.

    :return: None
    :rtype: None
    """

    with contextmanager(db_provider)() as session:
        lapsed_applications = get_lapses_applications(session)
        for application in lapsed_applications:
            with transaction_session_logger(session, "Error setting to lapsed"):
                application.status = ApplicationStatus.LAPSED
                application.application_lapsed_at = datetime.utcnow()
