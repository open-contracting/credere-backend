import logging
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.db.session import get_db

from . import application_utils

send_overdue_reminders = application_utils.send_overdue_reminders


def SLA_overdue_applications(db_privider: Session = get_db):
    logging.info("Sending SLA overdue reminder notifications")
    with contextmanager(db_privider)() as session:
        send_overdue_reminders(session)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Output logs to the console
    )
