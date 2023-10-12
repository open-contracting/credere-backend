import logging
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schema.core import Application

from . import application_utils

logger = logging.getLogger(__name__)

get_dated_applications = application_utils.get_dated_applications


def remove_dated_data(db_provider: Session = get_db):
    """
    Remove dated data from the database.

    This function retrieves applications with a decline, reject, or accepted status that are
    past their due date from the database. It removes sensitive data from these applications
    (e.g., primary_email) and sets the archived_at timestamp to the current UTC time. It also
    removes associated borrower documents.

    If the award associated with the application is not used in any other active applications,
    it will also be deleted from the database. Additionally, if the borrower is not associated
    with any other active applications, their personal information (legal_name, email, address,
    legal_identifier) will be cleared.

    :return: None
    :rtype: None
    """

    with contextmanager(db_provider)() as session:
        dated_applications = get_dated_applications(session)
        for application in dated_applications:
            try:
                # save to DB
                application.award.previous = True
                application.primary_email = ""
                application.archived_at = datetime.utcnow()

                for document in application.borrower_documents:
                    session.delete(document)

                # Check if there are any other active applications that use the same award
                active_applications_with_same_award = (
                    session.query(Application)
                    .filter(
                        Application.award_id == application.award_id,
                        Application.id != application.id,
                        Application.archived_at.is_(
                            None
                        ),  # Check that the application is active
                    )
                    .all()
                )
                # Delete the associated Award if no other active applications uses the award
                if len(active_applications_with_same_award) == 0:
                    application.borrower.legal_name = ""
                    application.borrower.email = ""
                    application.borrower.address = ""
                    application.borrower.legal_identifier = ""
                    application.borrower.source_data = ""

                session.commit()

            except Exception as e:
                logger.exception(f"there was an error deleting the data: {e}")
                session.rollback()
