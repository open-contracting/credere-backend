import logging
from contextlib import contextmanager

from app.core.settings import app_settings
from app.core.user_dependencies import sesClient
from app.db.session import get_db
from app.schema.core import Borrower
from app.utils import email_utility

from . import awards_utils
from .application_utils import create_application, insert_message
from .borrower_utils import get_or_create_borrower


def fetch_new_awards_from_date(last_updated_award_date: str, email_invitation: str):
    index = 0
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

                    message = insert_message(application, session)

                    # change in PROD
                    logging.info(f"Parameter email_invitation: {email_invitation}")
                    if not email_invitation or email_invitation == "":
                        email_invitation = app_settings.test_mail_receiver

                    logging.info(
                        f"NON PROD - Email to: {borrower.email} sent to {email_invitation}"
                    )

                    messageId = email_utility.send_invitation_email(
                        sesClient,
                        application.uuid,
                        email_invitation,  # change to borrower.email in prod
                        borrower.legal_name,
                        award.buyer_name,
                        award.title,
                    )
                    message.external_message_id = messageId
                    session.commit()
                    logging.info("Application created")
                except Exception as e:
                    logging.error(f"There was an error creating the application. {e}")
                    session.rollback()

        index += 1
        contracts_response = awards_utils.get_new_contracts(
            index, last_updated_award_date
        )
        contracts_response_json = contracts_response.json()


def fetch_new_awards(email_invitation: str = None):
    last_updated_award_date = awards_utils.get_last_updated_award_date()
    fetch_new_awards_from_date(last_updated_award_date, email_invitation)


def fetch_previous_awards(borrower: Borrower):
    contracts_response = awards_utils.get_previous_contracts(borrower.legal_identifier)
    contracts_response_json = contracts_response.json()

    if not contracts_response_json:
        logging.info(f"No previous contracts for {borrower.legal_identifier}")
        return

    logging.info(
        f"Previous contracts for {borrower.legal_identifier} response length: "
        + str(len(contracts_response_json))
    )
    for entry in contracts_response_json:
        with contextmanager(get_db)() as session:
            try:
                awards_utils.create_award(entry, session, borrower.id, True)
                session.commit()

            except Exception as e:
                logging.error(
                    f"There was an error creating the previous award for {borrower.legal_identifier}. {e}"
                )
                session.rollback()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Output logs to the console
    )
