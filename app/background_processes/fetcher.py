import logging
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.core.user_dependencies import sesClient
from app.db.session import get_db, transaction_session_logger
from app.exceptions import SkippedAwardError
from app.schema import core
from app.schema.core import Award, Borrower, BorrowerStatus, Message
from app.utils import email_utility

from . import background_utils
from . import colombia_data_access as data_access
from .application_utils import create_application

logger = logging.getLogger(__name__)


def _get_or_create_borrower(entry, session: Session) -> Borrower:
    """
    Get an existing borrower or create a new borrower based on the entry data.

    :param entry: The dictionary containing the borrower data.
    :type entry: dict
    :param session: The database session.
    :type session: Session

    :return: The existing or newly created borrower.
    :rtype: Borrower
    """

    documento_proveedor = data_access.get_documento_proveedor(entry)
    borrower_identifier = background_utils.get_secret_hash(documento_proveedor)
    data = data_access.create_new_borrower(borrower_identifier, documento_proveedor, entry)

    borrower = Borrower.first_by(session, "borrower_identifier", borrower_identifier)
    if borrower:
        if borrower.status == BorrowerStatus.DECLINE_OPPORTUNITIES:
            raise ValueError("Skipping Award - Borrower choosed to not receive any new opportunity")
        return borrower.update(session, **data)

    return Borrower.create(session, **data)


def _create_award(entry, session: Session, borrower_id=None, previous=False) -> Award:
    """
    Create a new award and insert it into the database.

    :param entry: The dictionary containing the award data.
    :type entry: dict
    :param session: The database session.
    :type session: Session
    :param borrower_id: The ID of the borrower associated with the award. (default: None)
    :type borrower_id: int, optional
    :param previous: Whether the award is a previous award or not. (default: False)
    :type previous: bool, optional

    :return: The inserted award.
    :rtype: Award
    """
    source_contract_id = data_access.get_source_contract_id(entry)

    if Award.first_by(session, "source_contract_id", source_contract_id):
        raise SkippedAwardError(f"[{previous=}] Award already exists with {source_contract_id=} ({entry=})")

    data = data_access.create_new_award(source_contract_id, entry, borrower_id, previous)

    return Award.create(session, **data)


def fetch_new_awards_from_date(last_updated_award_date: str, db_provider: Session, until_date: str = None):
    """
    Fetch new awards from the given date and process them.

    :param last_updated_award_date: Date string in the format 'YYYY-MM-DD'.
    :type last_updated_award_date: datetime
    """
    index = 0
    contracts_response = data_access.get_new_contracts(index, last_updated_award_date, until_date)
    contracts_response_json = contracts_response.json()

    if not contracts_response_json:
        logger.info("No new contracts")
        return
    total = 0
    while contracts_response.json():
        total += len(contracts_response_json)
        for entry in contracts_response_json:
            with contextmanager(db_provider)() as session:
                with transaction_session_logger(session, "Error creating the application"):
                    award = _create_award(entry, session)
                    borrower = _get_or_create_borrower(entry, session)
                    award.borrower_id = borrower.id

                    application = create_application(
                        award.id,
                        borrower.id,
                        borrower.email,
                        borrower.legal_identifier,
                        award.source_contract_id,
                        session,
                    )

                    message = Message.create(
                        session,
                        application=application,
                        type=core.MessageType.BORROWER_INVITACION,
                    )

                    messageId = email_utility.send_invitation_email(
                        sesClient,
                        application.uuid,
                        borrower.email,
                        borrower.legal_name,
                        award.buyer_name,
                        award.title,
                    )
                    message.external_message_id = messageId
        index += 1
        contracts_response = data_access.get_new_contracts(index, last_updated_award_date, until_date)
        contracts_response_json = contracts_response.json()
    logger.info("Total fetched contracts: %d", total)


def fetch_previous_awards(borrower: Borrower, db_provider: Session = get_db):
    """
    Fetch previous awards for a borrower that accepted an application. This wont generate an application,
    it will just insert the awards in our database

    :param borrower: The borrower for whom to fetch and process previous awards.
    :type borrower: Borrower
    """
    contracts_response = data_access.get_previous_contracts(borrower.legal_identifier)
    contracts_response_json = contracts_response.json()
    if not contracts_response_json:
        logger.info(f"No previous contracts for {borrower.legal_identifier}")
        return

    logger.info(
        f"Previous contracts for {borrower.legal_identifier} response length: " + str(len(contracts_response_json))
    )
    for entry in contracts_response_json:
        with contextmanager(db_provider)() as session:
            with transaction_session_logger(
                session,
                "Error creating the previous award for %s",
                borrower.legal_identifier,
            ):
                _create_award(entry, session, borrower.id, True)
