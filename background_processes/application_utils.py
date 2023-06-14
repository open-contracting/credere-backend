import logging
from contextlib import contextmanager
from datetime import datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.schema import core

from .background_utils import generate_uuid, get_secret_hash

DAYS_UNTIL_EXPIRED = 7

Application = core.Application()
ApplicationStatus = core.ApplicationStatus()
Message = core.Message()
MessageType = core.MessageType()


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


params = {"days_to_expire": 3}


def get_applications_to_remind_intro():
    with contextmanager(get_db)() as session:
        try:
            subquery = select(core.Message.application_id).where(
                core.Message.type == core.MessageType.BORROWER_PENDING_SUBMIT_REMINDER
            )
            users = (
                session.query(Application)
                .options(
                    joinedload(Application.borrower), joinedload(Application.award)
                )
                .filter(
                    and_(
                        Application.status == ApplicationStatus.PENDING,
                        Application.expired_at > datetime.now(),
                        Application.expired_at
                        <= datetime.now() + timedelta(days=params["days_to_expire"]),
                        ~Application.id.in_(subquery),
                    )
                )
                .all()
            )
        except SQLAlchemyError as e:
            raise e
    return users or []
