import logging
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.core.settings import app_settings
from app.core.user_dependencies import sesClient
from app.db.session import get_db
from app.schema.core import Borrower
from app.utils import email_utility

from . import awards_utils
from .application_utils import create_application, insert_message
from .borrower_utils import get_or_create_borrower


def fetch_new_awards_from_date(
    last_updated_award_date: str, email_invitation: str, db_provider: Session
):
    """
    Fetch new awards from the given date and process them.

    :param last_updated_award_date: Date string in the format 'YYYY-MM-DD'.
    :type last_updated_award_date: str
    :param email_invitation: Optional email address to send invitations. Defaults to None.
    :type email_invitation: str or None
    """
    index = 0
    contracts_response = awards_utils.get_new_contracts(index, last_updated_award_date)
    contracts_response_json = contracts_response.json()

    if not contracts_response_json:
        logging.info("No new contracts")
        return

    while len(contracts_response.json()) > 0:
        logging.info("Contracts response length: " + str(len(contracts_response_json)))
        for entry in contracts_response_json:
            with contextmanager(db_provider)() as session:
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

                    if app_settings.environment == "production":
                        if not email_invitation or email_invitation == "":
                            email_invitation = borrower.email
                    else:
                        email_invitation = app_settings.test_mail_receiver

                    logging.info(
                        f"{app_settings.environment} - Email to: {borrower.email} sent to {email_invitation}"
                    )

                    messageId = email_utility.send_invitation_email(
                        sesClient,
                        application.uuid,
                        email_invitation,
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


def fetch_new_awards(email_invitation: str = None, db_provider: Session = get_db):
    """
    Fetch new awards, checks if they exist in our database. If not it checks award's borrower and check if they exist.
    if either award and borrower doesn't exist or if borrower exist but the award doesn't it will create an application
    in status pending

    An email invitation will be sent to the proper borrower email obtained from endpoint data
    (In this case SECOP Colombia) for each application created

    you can also pass an email_invitation as parameter if you want to invite a particular borrower

    :param email_invitation: Optional email address to send invitations. Defaults to None.
    :type email_invitation: str or None
    """
    last_updated_award_date = awards_utils.get_last_updated_award_date()
    fetch_new_awards_from_date(last_updated_award_date, email_invitation, db_provider)


def fetch_previous_awards(borrower: Borrower, db_provider: Session = get_db):
    """
    Fetch previous awards for a borrower that accepted an application. This wont generate an application,
    it will just insert the awards in our database

    :param borrower: The borrower for whom to fetch and process previous awards.
    :type borrower: Borrower
    """
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
        with contextmanager(db_provider)() as session:
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
