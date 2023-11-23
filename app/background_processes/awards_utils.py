from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm.session import Session

from app.db.session import get_db
from app.exceptions import SkippedAwardError
from app.schema.core import Award

from . import background_utils
from . import colombia_data_access as data_access


def _get_existing_award(source_contract_id: str, session: Session):
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


def _insert_award(award: Award, session: Session):
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
    source_contract_id = data_access.get_source_contract_id(entry)

    # if award already exists
    if _get_existing_award(source_contract_id, session):
        raise SkippedAwardError(
            f"[{previous=}] Award already exists with {source_contract_id=} ({entry=})"
        )

    new_award = data_access.create_new_award(
        source_contract_id, entry, borrower_id, previous
    )

    award = _insert_award(new_award, session)

    return award
