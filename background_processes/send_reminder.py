import logging
from contextlib import contextmanager

from app.core.user_dependencies import sesClient
from app.db.session import get_db
from app.utils import email_utility

from .application_utils import get_applications_to_remind_intro
from .message_utils import update_message_type

if __name__ == "__main__":
    index = 0
    applications_to_send_intro_reminder = get_applications_to_remind_intro()
    print(len(applications_to_send_intro_reminder))
    if len(applications_to_send_intro_reminder) == 0:
        print("No new intro reminder to be sent")
    else:
        for application in applications_to_send_intro_reminder:
            with contextmanager(get_db)() as session:
                try:
                    # Db message table update
                    update_message_type(application.id, session)
                    uuid = application.uuid
                    email = application.primary_email
                    borrower_name = application.borrower.legal_name
                    buyer_name = application.award.buyer_name
                    title = application.award.title

                    email_utility.send_mail_intro_reminder(
                        sesClient, uuid, email, borrower_name, buyer_name, title
                    )
                    logging.info("Mail sent and status updated")
                    session.commit()
                except Exception as e:
                    print(
                        f"there was an error sending mail or updating the sent status: {e}"
                    )
                    session.rollback()
