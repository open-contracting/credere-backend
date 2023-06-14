import logging
from contextlib import contextmanager

from app.core.user_dependencies import sesClient
from app.db.session import get_db
from app.utils import email_utility

from . import awards_utils
from .application_utils import create_application, insert_message
from .borrower_utils import get_or_create_borrower


def fetch_awards():
    index = 0
    last_updated_award_date = awards_utils.get_last_updated_award_date()
    contracts_response = awards_utils.get_new_contracts(index, last_updated_award_date)
    contracts_response_json = contracts_response.json()

    if not contracts_response_json:
        logging.info("No new contracts")
        return

    while len(contracts_response.json()) > 0:
        logging.info("Contracts response length: " + str(len(contracts_response_json)))
        for entry in contracts_response_json:
            with contextmanager(get_db)() as session:
                try:
                    award = awards_utils.create_award(entry, session)
                    borrower = get_or_create_borrower(entry, session)
                    award.borrower_id = borrower.id

                    application = create_application(
                        award.id,
                        borrower.id,
                        borrower.email,
                        borrower.legal_identifier,
                        award.source_contract_id,
                        session,
                    )

                    insert_message(application, session)
                    session.commit()
                    logging.info("Application created")
                    email_utility.send_invitation_email(
                        sesClient,
                        application.uuid,
                        borrower.email,
                        borrower.legal_name,
                        award.buyer_name,
                        award.title,
                    )
                except Exception as e:
                    logging.error(f"There was an error creating the application. {e}")
                    session.rollback()

        index += 1
        contracts_response = awards_utils.get_new_contracts(
            index, last_updated_award_date
        )
        contracts_response_json = contracts_response.json()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Output logs to the console
    )
    fetch_awards()
