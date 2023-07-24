import logging
from contextlib import contextmanager

from sqlalchemy.orm import Session

from sqlalchemy.orm import Session

from app.core.user_dependencies import sesClient
from app.db.session import get_db
from app.utils import email_utility

from . import application_utils
from .message_utils import save_message_type

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
    logging.info(
        "Quantity of mails to send intro reminder "
        + str(len(applications_to_send_intro_reminder))
    )
    if len(applications_to_send_intro_reminder) == 0:
        logging.info("No new intro reminder to be sent")
    else:
        for application in applications_to_send_intro_reminder:
            with contextmanager(db_provider)() as session:
                try:
                    # save to DB
                    new_message = save_message_type(
                        application.id, session, "BORROWER_PENDING_APPLICATION_REMINDER"
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
                    logging.info("Mail sent and status updated")
                    session.commit()
                except Exception as e:
                    logging.error(
                        f"there was an error sending mail or updating the sent status: {e}"
                    )
                    session.rollback()

    applications_to_send_submit_reminder = get_applications_to_remind_submit(
        db_provider
    )
    logging.info(
        "Quantity of mails to send submit reminder "
        + str(len(applications_to_send_submit_reminder))
    )
    if len(applications_to_send_submit_reminder) == 0:
        logging.info("No new submit reminder to be sent")
    else:
        for application in applications_to_send_submit_reminder:
            with contextmanager(db_provider)() as session:
                try:
                    # Db message table update
                    new_message = save_message_type(
                        application.id, session, "BORROWER_PENDING_SUBMIT_REMINDER"
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
                    logging.info("Mail sent and status updated")
                    session.commit()
                except Exception as e:
                    logging.error(
                        f"there was an error sending mail or updating the sent status: {e}"
                    )
                    session.rollback()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Output logs to the console
    )
    send_reminders()
