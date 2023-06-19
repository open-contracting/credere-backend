import logging
from contextlib import contextmanager
from datetime import datetime

from app.db.session import get_db

from . import application_utils

get_applications_to_delete_data = application_utils.get_applications_to_delete_data


def remove_declined_rejected_accepted_data():
    with contextmanager(get_db)() as session:
        applications_to_delete_data = get_applications_to_delete_data(session)
        logging.info(
            "Quantity of decline, rejecte and accepted to remove data "
            + str(len(applications_to_delete_data))
        )
        if len(applications_to_delete_data) == 0:
            logging.info("No application to remove data")
        else:
            for application in applications_to_delete_data:
                try:
                    # save to DB
                    application.borrower.legal_name = ""
                    application.borrower.email = ""
                    application.borrower.address = ""
                    application.borrower.legal_identifier = ""

                    application.primary_email = ""
                    application.archived_at = datetime.utcnow()

                    for document in application.borrower_documents:
                        #     # Replace each field of document with an empty string or a null value
                        document.name = ""
                        document.file = b""
                        document.type = None
                    session.commit()

                except Exception as e:
                    logging.error(f"there was an error deleting the data: {e}")
                    print(e)
                    session.rollback()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Output logs to the console
    )
    remove_declined_rejected_accepted_data()
