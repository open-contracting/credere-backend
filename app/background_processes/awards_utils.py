from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm.session import Session

from app.db.session import get_db
from app.schema.core import Award

from . import background_utils
from . import colombia_data_access as data_access


def get_existing_award(source_contract_id: str, session: Session):
    """
    Get an existing award based on the source contract ID.

    :param source_contract_id: The unique identifier for the award's source contract.
    :type source_contract_id: str
    :param session: The database session.
    :type session: Session

    :return: The existing award if found, otherwise None.
    :rtype: Award or None
    """

    award = (
        session.query(Award)
        .filter(Award.source_contract_id == source_contract_id)
        .first()
    )

    return award


def get_last_updated_award_date():
    """
    Get the date of the last updated award.

    :return: The last updated award date.
    :rtype: datetime or None
    """
    with contextmanager(get_db)() as session:
        award = (
            session.query(Award).order_by(desc(Award.source_last_updated_at)).first()
        )

        if not award:
            return None

        return award.source_last_updated_at


def insert_award(award: Award, session: Session):
    """
    Insert a new award into the database.

    :param award: The award data to be inserted.
    :type award: Award

    :param session: The database session.
    :type session: Session

    :return: The inserted award.
    :rtype: Award
    """

    obj_db = Award(**award)
    obj_db.created_at = datetime.utcnow()
    obj_db.missing_data = background_utils.get_missing_data_keys(award)

    session.add(obj_db)
    session.flush()
    return obj_db


def create_new_award(
    source_contract_id: str,
    entry: dict,
    borrower_id: int = None,
    previous: bool = False,
) -> dict:
    """
    Create a new award.

    :param source_contract_id: The unique identifier for the award's source contract.
    :type source_contract_id: str

    :param entry: The dictionary containing the award data.
    :type entry: dict

    :param borrower_id: The ID of the borrower associated with the award. (default: None)
    :type borrower_id: int, optional

    :param previous: Whether the award is a previous award or not. (default: False)
    :type previous: bool, optional

    :return: The newly created award.
    :rtype: dict
    """

    return data_access.create_new_award(
        source_contract_id, entry, borrower_id, previous
    )


def get_new_contracts(index: int, last_updated_award_date, until_date = None):
    """
    Get new contracts starting from the specified index and last updated award date.

    :param index: The index from which to start fetching new contracts.
    :type index: int
    :param last_updated_award_date: The date of the last updated award.
    :type last_updated_award_date: datetime

    :return: The new contracts.
    :rtype: [dict]
    """

    return data_access.get_new_contracts(index, last_updated_award_date, until_date)


def get_previous_contracts(documento_proveedor):
    """
    Get previous contracts for a given provider document.

    :param documento_proveedor: The provider document for which to fetch previous contracts.
    :type documento_proveedor: str

    :return: The previous contracts.
    :rtype: [dict]
    """

    return data_access.get_previous_contracts(documento_proveedor)


def get_source_contract_id(entry):
    """
    Get the source contract ID from the entry.

    :param entry: The entry containing the source contract ID.
    :type entry: dict

    :return: The source contract ID.
    :rtype: str
    """

    return data_access.get_source_contract_id(entry)


def create_award(entry, session: Session, borrower_id=None, previous=False) -> Award:
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
    source_contract_id = get_source_contract_id(entry)

    # if award already exists
    if get_existing_award(source_contract_id, session):
        background_utils.raise_sentry_error(
            f"Skipping Award [previous {previous}] - Already exists on database", entry
        )

    new_award = create_new_award(source_contract_id, entry, borrower_id, previous)

    award = insert_award(new_award, session)

    return award
