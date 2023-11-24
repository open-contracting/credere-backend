import logging
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.core.user_dependencies import sesClient
from app.db.session import get_db, transaction_session_logger
from app.schema import core
from app.schema.core import Message
from app.utils import email_utility

from . import application_utils

logger = logging.getLogger(__name__)

get_applications_to_remind_intro = application_utils.get_applications_to_remind_intro
get_applications_to_remind_submit = application_utils.get_applications_to_remind_submit


def send_reminders(db_provider: Session = get_db):
    """
    Send reminders to borrowers.

    This function retrieves applications that require a reminder email to be sent to the borrowers.
    It first retrieves applications that need an introduction reminder and sends the emails. Then,
    it retrieves applications that need a submit reminder and sends those emails as well.

    For each application, it saves the message type (BORROWER_PENDING_APPLICATION_REMINDER or
    BORROWER_PENDING_SUBMIT_REMINDER) to the database and updates the external_message_id after
    the email has been sent successfully.

    :return: None
    :rtype: None
    """

    applications_to_send_intro_reminder = get_applications_to_remind_intro(db_provider)
    logger.info(
        "Quantity of mails to send intro reminder "
        + str(len(applications_to_send_intro_reminder))
    )
    if len(applications_to_send_intro_reminder) == 0:
        logger.info("No new intro reminder to be sent")
    else:
        for application in applications_to_send_intro_reminder:
            with contextmanager(db_provider)() as session:
                with transaction_session_logger(
                    session, "Error sending mail or updating the sent status"
                ):
                    new_message = Message.create(
                        session,
                        application=application,
                        type=core.MessageType.BORROWER_PENDING_APPLICATION_REMINDER,
                    )
                    uuid = application.uuid
                    email = application.primary_email
                    borrower_name = application.borrower.legal_name
                    buyer_name = application.award.buyer_name
                    title = application.award.title

                    messageID = email_utility.send_mail_intro_reminder(
                        sesClient, uuid, email, borrower_name, buyer_name, title
                    )
                    new_message.external_message_id = messageID
                    logger.info("Mail sent and status updated")

    applications_to_send_submit_reminder = get_applications_to_remind_submit(
        db_provider
    )
    logger.info(
        "Quantity of mails to send submit reminder "
        + str(len(applications_to_send_submit_reminder))
    )
    if len(applications_to_send_submit_reminder) == 0:
        logger.info("No new submit reminder to be sent")
    else:
        for application in applications_to_send_submit_reminder:
            with contextmanager(db_provider)() as session:
                with transaction_session_logger(
                    session, "Error sending mail or updating the sent status"
                ):
                    # Db message table update
                    new_message = Message.create(
                        session,
                        application=application,
                        type=core.MessageType.BORROWER_PENDING_SUBMIT_REMINDER,
                    )
                    uuid = application.uuid
                    email = application.primary_email
                    borrower_name = application.borrower.legal_name
                    buyer_name = application.award.buyer_name
                    title = application.award.title

                    messageID = email_utility.send_mail_submit_reminder(
                        sesClient, uuid, email, borrower_name, buyer_name, title
                    )
                    new_message.external_message_id = messageID
                    logger.info("Mail sent and status updated")
