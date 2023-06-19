import logging
from contextlib import contextmanager

from app.db.session import get_db

from . import application_utils

get_applications_to_delete_data = application_utils.get_applications_to_delete_data


def remove_data_from_declined():
    applications_to_delete_data = get_applications_to_delete_data()
    logging.info(
        "Quantity of declined apps to delete data"
        + str(len(applications_to_delete_data))
    )
    if len(applications_to_delete_data) == 0:
        logging.info("No new intro reminder to be sent")
    else:
        for application in applications_to_delete_data:
            with contextmanager(get_db)() as session:
                try:
                    # save to DB
                    application.borrower.legal_name = ""
                    application.borrower.email = ""
                    application.borrower.address = ""
                    application.borrower.legal_identifier = ""
                    application.primary_email = ""

                    for document in application.borrower_documents:
                        # Replace each field of document with an empty string or a null value
                        document.name = ""
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
    remove_data_from_declined()
