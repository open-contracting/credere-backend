import logging
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.core.user_dependencies import sesClient
from app.db.session import get_db
from app.schema.core import Borrower
from app.utils import email_utility

from . import awards_utils
from .application_utils import create_application, insert_message
from .borrower_utils import get_or_create_borrower

logger = logging.getLogger(__name__)


def fetch_new_awards_from_date(
    last_updated_award_date: str, db_provider: Session, until_date: str = None
):
    """
    Fetch new awards from the given date and process them.

    :param last_updated_award_date: Date string in the format 'YYYY-MM-DD'.
    :type last_updated_award_date: datetime
    """
    index = 0
    contracts_response = awards_utils.get_new_contracts(
        index, last_updated_award_date, until_date
    )
    contracts_response_json = contracts_response.json()

    if not contracts_response_json:
        logger.info("No new contracts")
        return
    total = 0
    while contracts_response.json():
        total += len(contracts_response_json)
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

                    messageId = email_utility.send_invitation_email(
                        sesClient,
                        application.uuid,
                        borrower.email,
                        borrower.legal_name,
                        award.buyer_name,
                        award.title,
                    )
                    message.external_message_id = messageId
                    session.commit()
                    logger.info("Application created")
                except Exception as e:
                    logger.exception(
                        f"There was an error creating the application. {e}"
                    )
                    session.rollback()
        index += 1
        contracts_response = awards_utils.get_new_contracts(
            index, last_updated_award_date, until_date
        )
        contracts_response_json = contracts_response.json()
    logger.info("Total fetched contracts: %d", total)


def fetch_new_awards(db_provider: Session = get_db):
    """
    Fetch new awards, checks if they exist in our database. If not it checks award's borrower and check if they exist.
    if either award and borrower doesn't exist or if borrower exist but the award doesn't it will create an application
    in status pending

    An email invitation will be sent to the proper borrower email obtained from endpoint data
    (In this case SECOP Colombia) for each application created

    you can also pass an email_invitation as parameter if you want to invite a particular borrower
    """
    last_updated_award_date = awards_utils.get_last_updated_award_date()
    fetch_new_awards_from_date(last_updated_award_date, db_provider)


def fetch_contracts_from_date(
    from_date: str, until_date: str, db_provider: Session = get_db
):
    fetch_new_awards_from_date(from_date, db_provider, until_date)


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
        logger.info(f"No previous contracts for {borrower.legal_identifier}")
        return

    logger.info(
        f"Previous contracts for {borrower.legal_identifier} response length: "
        + str(len(contracts_response_json))
    )
    for entry in contracts_response_json:
        with contextmanager(db_provider)() as session:
            try:
                awards_utils.create_award(entry, session, borrower.id, True)
                session.commit()

            except Exception as e:
                logger.exception(
                    f"There was an error creating the previous award for {borrower.legal_identifier}. {e}"
                )
                session.rollback()
