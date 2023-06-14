import logging
from contextlib import contextmanager
from datetime import datetime, timedelta

from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.session import Session

from app.db.session import get_db
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


params = {"days_to_expire": 3}


# hacer un query que me traiga todas las aplicaciones que esteen en estado
# sin accederse por primera  vez y que su expiry date sea igual o menor a 3 dias (parametro)
# select user email from applications where status = pending and expiry_date <= 3 days
def get_users_to_remind_Access_to_credit():
    with contextmanager(get_db)() as session:
        try:
            users = (
                session.query(Application)
                .filter(
                    and_(
                        Application.status.PENDING,
                        Application.expired_at > datetime.now(),
                        Application.expired_at
                        <= datetime.now() + timedelta(days=params.days_to_expire),
                        # filtro de la tabla message
                        # message.type == BORROWER_PENDING_APPLICATION_REMINDER
                    )
                )
                .all()
            )
            print("THIS ARE THE USERS")
            print(users)
        except SQLAlchemyError as e:
            raise e
    return users or []
