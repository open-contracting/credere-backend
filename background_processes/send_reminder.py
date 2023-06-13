from contextlib import contextmanager

# from app.core.user_dependencies import sesClient
from app.db.session import get_db, transaction_session

from .application_utils import get_users_to_remind_Access_to_credit

# from app.utils import email_utility


# from .application_utils import create_application
# from .awards_utils import get_new_contracts, get_or_create_award
# from .background_utils import raise_sentry_error
# from .borrower_utils import get_or_create_borrower

if __name__ == "__main__":
    index = 0
    user_to_send_reminder = get_users_to_remind_Access_to_credit()
    print(len(user_to_send_reminder))
    if len(user_to_send_reminder) == 0:
        print("No new reminder to be sent")
    else:
        with contextmanager(get_db)() as session:
            with transaction_session(session):
                for entry in user_to_send_reminder:
                    try:
                        print("entry", entry.mail)
                    except Exception as e:
                        print(f"An error occurred: {e}")
                        #    todo create function to store sent status on application
                        #  Application.reminder_sent = true

                        # email_utility.send_access_to_credit_reminder(
                        #     sesClient, uuid, email, borrower_name, buyer_name, title
                        # )
                    #     console("Mail sent and status updated")
                    # except ValueError as e:
                    #     print(
                    #         "there was an error sending mail or updating the sent status",
                    #         e,
                    #     )
