from sqlalchemy.orm.session import Session

from app.schema import core
from app.schema.core import Message


def save_message_type(application_id: int, session: Session, message):
    try:
        # Create a new message
        new_message = Message(
            application_id=application_id, type=getattr(core.MessageType, message)
        )

        # Add new message to the session
        session.add(new_message)
        session.flush()
        return new_message
    except Exception as e:
        raise e
