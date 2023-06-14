from contextlib import contextmanager

from app.db.session import get_db
from app.schema import core
from app.schema.core import Message

# from datetime import datetime, timedelta

# from sqlalchemy import and_, select
# from sqlalchemy.exc import SQLAlchemyError


def update_message_type(message_id: int):
    with contextmanager(get_db)() as session:
        try:
            # Fetch the specific message by id
            message_to_update = session.query(Message).get(message_id)

            # If the message exists, update its type
            if message_to_update:
                message_to_update.type = core.BorrowerDocumentType.BANK_NAME
                # Commit the changes
                session.commit()
            else:
                print(f"No message found for id {message_id}")

        except Exception as e:
            session.rollback()
            raise e
