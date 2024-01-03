import logging
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Callable, Generator

from sqlalchemy.orm import Session

from app import mail, models, util
from app.aws import sesClient
from app.db import get_db, handle_skipped_award
from app.exceptions import SkippedAwardError
from app.settings import app_settings
from app.sources import colombia as data_access

logger = logging.getLogger(__name__)

DAYS_UNTIL_EXPIRED = 7

ApplicationStatus = models.ApplicationStatus


def _create_application(
    award_id: int | None,
    borrower_id: int | None,
    email: str,
    legal_identifier: str,
    source_contract_id: str,
    session: Session,
) -> models.Application:
    """
    Create a new application and insert it into the database.

    :param award_id: The ID of the award associated with the application.
    :param borrower_id: The ID of the borrower associated with the application.
    :param email: The email of the borrower.
    :param legal_identifier: The legal identifier of the borrower.
    :param source_contract_id: The ID of the source contract.
    :return: The created application.
    """
    award_borrower_identifier: str = util.get_secret_hash(f"{legal_identifier}{source_contract_id}")

    application = models.Application.first_by(session, "award_borrower_identifier", award_borrower_identifier)
    if application:
        raise SkippedAwardError(f"{application.id=} already exists for {legal_identifier=} {source_contract_id=}")

    new_uuid: str = util.generate_uuid(award_borrower_identifier)
    data = {
        "award_id": award_id,
        "borrower_id": borrower_id,
        "primary_email": email,
        "award_borrower_identifier": award_borrower_identifier,
        "uuid": new_uuid,
        "expired_at": datetime.utcnow() + timedelta(days=app_settings.application_expiration_days),
    }

    return models.Application.create(session, **data)


def _get_or_create_borrower(entry: dict[str, Any], session: Session) -> models.Borrower:
    """
    Get an existing borrower or create a new borrower based on the entry data.

    :param entry: The dictionary containing the borrower data.
    :return: The existing or newly created borrower.
    """

    documento_proveedor = data_access.get_documento_proveedor(entry)
    borrower_identifier = util.get_secret_hash(documento_proveedor)
    data = data_access.get_borrower(borrower_identifier, documento_proveedor, entry)

    borrower = models.Borrower.first_by(session, "borrower_identifier", borrower_identifier)
    if borrower:
        if borrower.status == models.BorrowerStatus.DECLINE_OPPORTUNITIES:
            raise ValueError("Skipping Award - Borrower chose to not receive any new opportunity")
        return borrower.update(session, **data)

    return models.Borrower.create(session, **data)


def _create_award(
    entry: dict[str, Any], session: Session, borrower_id: int | None = None, previous: bool = False
) -> models.Award:
    """
    Create a new award and insert it into the database.

    :param entry: The dictionary containing the award data.
    :param borrower_id: The ID of the borrower associated with the award. (default: None)
    :param previous: Whether the award is a previous award or not. (default: False)
    :return: The inserted award.
    """
    source_contract_id = data_access.get_source_contract_id(entry)

    if models.Award.first_by(session, "source_contract_id", source_contract_id):
        raise SkippedAwardError(f"[{previous=}] Award already exists with {source_contract_id=} ({entry=})")

    data = data_access.get_award(source_contract_id, entry, borrower_id, previous)

    return models.Award.create(session, **data)


def _create_complete_application(contract_response, db_provider: Callable[[], Generator[Session, None, None]]) -> None:
    with contextmanager(db_provider)() as session:
        with handle_skipped_award(session, "Error creating the application"):
            award = _create_award(contract_response, session)
            borrower = _get_or_create_borrower(contract_response, session)
            award.borrower_id = borrower.id

            application = _create_application(
                award.id,
                borrower.id,
                borrower.email,
                borrower.legal_identifier,
                award.source_contract_id,
                session,
            )

            message = models.Message.create(
                session,
                application=application,
                type=models.MessageType.BORROWER_INVITATION,
            )

            message_id = mail.send_invitation_email(
                sesClient,
                application.uuid,
                borrower.email,
                borrower.legal_name,
                award.buyer_name,
                award.title,
            )
            message.external_message_id = message_id

            session.commit()


def fetch_new_awards_from_date(
    last_updated_award_date: datetime,
    db_provider: Callable[[], Generator[Session, None, None]],
    until_date: datetime | None = None,
) -> None:
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
    while contracts_response_json:
        total += len(contracts_response_json)
        for entry in contracts_response_json:
            _create_complete_application(entry, db_provider)
        index += 1
        contracts_response = data_access.get_new_contracts(index, last_updated_award_date, until_date)
        contracts_response_json = contracts_response.json()
    logger.info("Total fetched contracts: %d", total)


def fetch_award_by_contract_and_supplier(
    contract_id: str, supplier_id: str, db_provider: Callable[[], Generator[Session, None, None]]
) -> None:
    contract_response = data_access.get_contract_by_contract_and_supplier(contract_id, supplier_id).json()
    if not contract_response:
        logger.info(f"The contract with id {contract_id} and supplier id {supplier_id} was not found")
        return
    _create_complete_application(contract_response[0], db_provider)


def fetch_previous_awards(
    borrower: models.Borrower, db_provider: Callable[[], Generator[Session, None, None]] = get_db
) -> None:
    """
    Fetch previous awards for a borrower that accepted an application. This wont generate an application,
    it will just insert the awards in our database

    :param borrower: The borrower for whom to fetch and process previous awards.
    """
    contracts_response = data_access.get_previous_contracts(borrower.legal_identifier)
    contracts_response_json = contracts_response.json()
    if not contracts_response_json:
        logger.info("No previous contracts for %s", borrower.legal_identifier)
        return

    logger.info(
        "Previous contracts for %s response length: %s", borrower.legal_identifier, len(contracts_response_json)
    )
    for entry in contracts_response_json:
        with contextmanager(db_provider)() as session:
            with handle_skipped_award(session, "Error creating the previous award for %s", borrower.legal_identifier):
                _create_award(entry, session, borrower.id, True)

                session.commit()
