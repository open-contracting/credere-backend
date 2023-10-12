from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.db.session import get_db

from . import application_utils

send_overdue_reminders = application_utils.send_overdue_reminders


def SLA_overdue_applications(db_privider: Session = get_db):
    """
    Send SLA (Service Level Agreement) overdue reminders to borrowers.

    This function sends overdue reminders to borrowers for applications that have breached the
    Service Level Agreement (SLA). It first calls the `send_overdue_reminders()` function from the
    `application_utils` module, passing the database session as an argument to retrieve the
    applications that need the overdue reminders.

    The `send_overdue_reminders()` function sends the overdue reminders to the borrowers and
    handles updating the relevant information in the database.

    :return: None
    :rtype: None
    """

    with contextmanager(db_privider)() as session:
        send_overdue_reminders(session)
