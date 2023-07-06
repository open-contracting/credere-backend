import logging
from contextlib import contextmanager
from datetime import datetime

from app.db.session import get_db
from app.schema.core import Application

from . import application_utils

get_dated_applications = application_utils.get_dated_applications


def remove_dated_data():
    with contextmanager(get_db)() as session:
        dated_applications = get_dated_applications(session)
        logging.info(
            "Quantity of decline, rejecte and accepted to remove data "
            + str(len(dated_applications))
        )
        if len(dated_applications) == 0:
            logging.info("No application to remove data")
        else:
            for application in dated_applications:
                try:
                    # save to DB
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
                        session.delete(application.award)
                        application.borrower.legal_name = ""
                        application.borrower.email = ""
                        application.borrower.address = ""
                        application.borrower.legal_identifier = ""
                    session.commit()

                except Exception as e:
                    logging.error(f"there was an error deleting the data: {e}")
                    session.rollback()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Output logs to the console
    )
    remove_dated_data()
