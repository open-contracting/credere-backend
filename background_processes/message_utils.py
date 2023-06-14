from sqlalchemy.orm.session import Session

from app.schema import core
from app.schema.core import Message


def update_message_type(message_id: int, session: Session):
    try:
        # Fetch the specific message by id
        message_to_update = session.query(Message).get(message_id)

        # If the message exists, update its type
        if message_to_update:
            message_to_update.type = core.MessageType.BORROWER_PENDING_SUBMIT_REMINDER
            session.flush()
        else:
            print(f"No message found for id {message_id}")

    except Exception as e:
        raise e
