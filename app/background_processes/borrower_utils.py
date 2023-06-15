from datetime import datetime

from sqlalchemy.orm.session import Session

from app.schema.core import Borrower, BorrowerStatus

from . import background_utils
from . import colombia_data_access as data_access


def get_borrower(borrower_identifier: str, session: Session) -> int:
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


def insert_borrower(borrower: Borrower, session: Session) -> int:
    obj_db = Borrower(**borrower)
    obj_db.created_at = datetime.utcnow()
    obj_db.missing_data = background_utils.get_missing_data_keys(borrower)

    session.add(obj_db)
    session.flush()

    return obj_db


def update_borrower(
    original_borrower: Borrower, borrower: dict, session: Session
) -> int:
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


def create_new_borrower(
    borrower_identifier: str, documento_proveedor: str, entry: dict
) -> dict:
    return data_access.create_new_borrower(
        borrower_identifier, documento_proveedor, entry
    )


def get_documento_proveedor(entry) -> str:
    return data_access.get_documento_proveedor(entry)


def get_or_create_borrower(entry, session: Session) -> Borrower:
    documento_proveedor = get_documento_proveedor(entry)
    borrower_identifier = background_utils.get_secret_hash(documento_proveedor)
    new_borrower = create_new_borrower(borrower_identifier, documento_proveedor, entry)

    # existing borrower
    original_borrower = get_borrower(borrower_identifier, session)
    if original_borrower:
        return update_borrower(original_borrower, new_borrower, session)

    return insert_borrower(new_borrower, session)
