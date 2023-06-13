import logging
from datetime import datetime, timedelta

from sqlalchemy.orm.session import Session

from app.schema.core import Application, Message, MessageType

from .background_utils import generate_uuid, get_secret_hash

DAYS_UNTIL_EXPIRED = 7


def insert_application(application: Application, session: Session):
    obj_db = Application(**application)
    obj_db.created_at = datetime.utcnow()

    session.add(obj_db)
    session.flush()

    return obj_db


def insert_message(application: Application, session: Session):
    obj_db = Message(application=application, type=MessageType.BORROWER_INVITACION)
    obj_db.created_at = datetime.utcnow()

    session.add(obj_db)
    session.flush()

    return obj_db


def create_application(
    award_id, borrower_id, email, legal_identifier, source_contract_id, session: Session
) -> Application:
    award_borrower_identifier: str = get_secret_hash(
        legal_identifier + source_contract_id
    )
    new_uuid: str = generate_uuid(award_borrower_identifier)
    application = {
        "award_id": award_id,
        "borrower_id": borrower_id,
        "primary_email": email,
        "award_borrower_identifier": award_borrower_identifier,
        "uuid": new_uuid,
        "expired_at": datetime.utcnow() + timedelta(days=DAYS_UNTIL_EXPIRED),
    }
    try:
        application = insert_application(application, session)
    except Exception as e:
        logging.error(f"Error creating application {e}")
        raise e

    return application
