from sqlalchemy.orm import Session

from app.exceptions import SkippedAwardError
from app.schema.core import Award

from . import colombia_data_access as data_access


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
