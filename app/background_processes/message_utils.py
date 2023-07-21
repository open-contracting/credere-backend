from sqlalchemy.orm.session import Session

from app.schema import core
from app.schema.core import Message


def save_message_type(application_id: int, session: Session, message):
    """
    Create and save a new message associated with a specific application in the database.

    This function takes an `application_id`, an active database session (`session`),
    and a message type (`message`) as input. It creates a new `Message` instance with
    the provided `application_id` and the corresponding `MessageType`. The `MessageType`
    is determined based on the `message` parameter, which should be a valid string
    representing the message type (e.g., 'BORROWER_PENDING_APPLICATION_REMINDER',
    'BORROWER_PENDING_SUBMIT_REMINDER', etc.).

    The newly created message is added to the database session (`session`) and then
    immediately flushed to the database. The function returns the new message instance
    after it has been saved to the database.

    If an error occurs during the process, it is caught and raised. The caller of this
    function should handle any exceptions appropriately.

    Parameters:
        application_id (int): The ID of the application associated with the message.
        session (Session): An active SQLAlchemy session to interact with the database.
        message (str): A string representing the message type (e.g., 'BORROWER_PENDING_APPLICATION_REMINDER').

    Returns:
        Message: The newly created `Message` instance after saving to the database.

    Raises:
        Exception: If there is an error during the creation or saving of the message.
        (Note: It is generally not recommended to catch a generic `Exception` in the caller.)
    """
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
