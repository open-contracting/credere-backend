from contextlib import contextmanager
from datetime import datetime, timedelta

from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.schema.core import Application

from .background_utils import generate_uuid, get_secret_hash

DAYS_UNTIL_EXPIRED = 7


def insert_application(application: Application):
    with contextmanager(get_db)() as session:
        try:
            obj_db = Application(**application)
            session.add(obj_db)
            session.commit()
            session.refresh(obj_db)
            return obj_db.id
        except SQLAlchemyError as e:
            raise e


def create_application(
    award_id, borrower_id, email, legal_identifier, source_contract_id
) -> str:
    award_borrowed_identifier: str = get_secret_hash(
        legal_identifier + source_contract_id
    )
    new_uuid: str = generate_uuid(award_borrowed_identifier)
    application = {
        "award_id": award_id,
        "borrower_id": borrower_id,
        "primary_email": email,
        "award_borrowed_identifier": award_borrowed_identifier,
        "uuid": new_uuid,
        "expired_at": datetime.utcnow() + timedelta(days=DAYS_UNTIL_EXPIRED),
    }
    insert_application(application)
    return new_uuid
