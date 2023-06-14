import logging
from datetime import datetime, timedelta

from sqlalchemy.orm.session import Session

from app.schema.core import Application, Message, MessageType

from . import background_utils

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


def get_existing_application(award_borrower_identifier: str, session: Session):
    application = (
        session.query(Application)
        .filter(Application.award_borrower_identifier == award_borrower_identifier)
        .first()
    )

    return application


def create_application(
    award_id, borrower_id, email, legal_identifier, source_contract_id, session: Session
) -> Application:
    award_borrower_identifier: str = background_utils.get_secret_hash(
        legal_identifier + source_contract_id
    )

    # if application already exists
    application = get_existing_application(award_borrower_identifier, session)
    if application:
        error_data = {
            "legal_identifier": legal_identifier,
            "source_contract_id": source_contract_id,
            "application_id": application.id,
        }

        background_utils.raise_sentry_error(
            f"Skipping Award - Application ID {application.id} already exists on for award {source_contract_id}",
            error_data,
        )

    new_uuid: str = background_utils.generate_uuid(award_borrower_identifier)
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
