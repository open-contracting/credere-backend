import logging
from datetime import datetime, timedelta

from sqlalchemy import and_, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.db.session import app_settings
from app.schema import core
from app.schema.core import Application, Message, MessageType

from . import background_utils

ApplicationStatus = core.ApplicationStatus


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
        "expired_at": datetime.utcnow()
        + timedelta(days=app_settings.application_expiration_days),
    }

    application = insert_application(application, session)

    return application


def get_applications_to_delete_data(session):
    try:
        days_to_delete_data = datetime.now() - timedelta(
            days=app_settings.days_to_erase_borrower_data
        )
        applications_to_remove_data = (
            session.query(Application)
            .options(
                joinedload(Application.borrower),
                joinedload(Application.borrower_documents),
            )
            .filter(
                or_(
                    and_(
                        Application.status == ApplicationStatus.DECLINED,
                        Application.borrower_declined_at < days_to_delete_data,
                    ),
                    and_(
                        Application.status == ApplicationStatus.REJECTED,
                        Application.lender_rejected_at < days_to_delete_data,
                    ),
                    and_(
                        Application.status == ApplicationStatus.COMPLETED,
                        Application.lender_approved_at < days_to_delete_data,
                    ),
                ),
                Application.archived_at.is_(None),
            )
            .all()
        )
        logging.info(applications_to_remove_data)
    except SQLAlchemyError as e:
        raise e

    return applications_to_remove_data or []
