from contextlib import contextmanager

from app.core.user_dependencies import sesClient
from app.db.session import get_db
from app.utils import email_utility

from . import application_utils
from .message_utils import save_message_type

get_applications_to_remind_intro = application_utils.get_applications_to_remind_intro
get_applications_to_remind_submit = application_utils.get_applications_to_remind_submit

if __name__ == "__main__":
    applications_to_send_intro_reminder = get_applications_to_remind_intro()
    print(
        "Quantity of mails to send intro reminder "
        + str(len(applications_to_send_intro_reminder))
    )
    if len(applications_to_send_intro_reminder) == 0:
        print("No new intro reminder to be sent")
    else:
        for application in applications_to_send_intro_reminder:
            with contextmanager(get_db)() as session:
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
                    print("Mail sent and status updated")
                    session.commit()
                except Exception as e:
                    print(
                        f"there was an error sending mail or updating the sent status: {e}"
                    )
                    session.rollback()

    applications_to_send_submit_reminder = get_applications_to_remind_submit()
    print(
        "Quantity of mails to send submit reminder "
        + str(len(applications_to_send_submit_reminder))
    )
    if len(applications_to_send_submit_reminder) == 0:
        print("No new submit reminder to be sent")
    else:
        for application in applications_to_send_submit_reminder:
            with contextmanager(get_db)() as session:
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
                    print("Mail sent and status updated")
                    session.commit()
                except Exception as e:
                    print(
                        f"there was an error sending mail or updating the sent status: {e}"
                    )
                    session.rollback()
