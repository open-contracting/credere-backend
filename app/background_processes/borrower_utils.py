from datetime import datetime

from sqlalchemy.orm.session import Session

from app.schema.core import Borrower, BorrowerStatus

from . import background_utils
from . import colombia_data_access as data_access


def _get_borrower(borrower_identifier: str, session: Session) -> int:
    """
    Get the borrower based on the borrower identifier.

    :param borrower_identifier: The unique identifier for the borrower.
    :type borrower_identifier: str
    :param session: The database session.
    :type session: Session

    :return: The borrower if found, otherwise None.
    :rtype: Borrower or None
    """

    obj = (
        session.query(Borrower)
        .filter(Borrower.borrower_identifier == borrower_identifier)
        .first()
    )
    if not obj:
        return None

    if obj.status == BorrowerStatus.DECLINE_OPPORTUNITIES:
        raise ValueError(
            "Skipping Award - Borrower choosed to not receive any new opportunity"
        )

    return obj


def _insert_borrower(borrower: Borrower, session: Session) -> int:
    """
    Insert a new borrower into the database.

    :param borrower: The borrower data to be inserted.
    :type borrower: Borrower
    :param session: The database session.
    :type session: Session

    :return: The inserted borrower.
    :rtype: Borrower
    """

    obj_db = Borrower(**borrower)
    obj_db.created_at = datetime.utcnow()
    obj_db.missing_data = background_utils.get_missing_data_keys(borrower)

    session.add(obj_db)
    session.flush()

    return obj_db


def _update_borrower(
    original_borrower: Borrower, borrower: dict, session: Session
) -> int:
    """
    Update an existing borrower in the database.

    :param original_borrower: The original borrower object to be updated.
    :type original_borrower: Borrower
    :param borrower: The updated borrower data as a dictionary.
    :type borrower: dict
    :param session: The database session.
    :type session: Session

    :return: The updated borrower.
    :rtype: Borrower
    """

    original_borrower.legal_name = borrower.get("legal_name", "")
    original_borrower.email = borrower.get("email", "")
    original_borrower.address = borrower.get("address", "")
    original_borrower.legal_identifier = borrower.get("legal_identifier", "")
    original_borrower.type = borrower.get("type", "")
    original_borrower.source_data = borrower.get("source_data", "")
    original_borrower.missing_data = background_utils.get_missing_data_keys(borrower)

    session.refresh(original_borrower)
    session.flush()

    return original_borrower


def get_or_create_borrower(entry, session: Session) -> Borrower:
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
    new_borrower = data_access.create_new_borrower(
        borrower_identifier, documento_proveedor, entry
    )

    # existing borrower
    original_borrower = _get_borrower(borrower_identifier, session)
    if original_borrower:
        return _update_borrower(original_borrower, new_borrower, session)

    return _insert_borrower(new_borrower, session)
