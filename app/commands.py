import logging
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime

import typer

from app import background_processes, mail
from app.aws import sesClient
from app.background_processes import application_utils
from app.db import get_db, transaction_session, transaction_session_logger
from app.schema import core
from app.schema.core import Application, ApplicationStatus, Award, Message
from app.settings import app_settings

logger = logging.getLogger(__name__)

app = typer.Typer()


@app.command()
def fetch_awards():
    """
    Fetch new awards, checks if they exist in our database. If not it checks award's borrower and check if they exist.
    if either award and borrower doesn't exist or if borrower exist but the award doesn't it will create an application
    in status pending

    An email invitation will be sent to the proper borrower email obtained from endpoint data
    (In this case SECOP Colombia) for each application created

    you can also pass an email_invitation as parameter if you want to invite a particular borrower
    """
    with contextmanager(get_db)() as session:
        last_updated_award_date = Award.last_updated(session)
    background_processes.fetcher.fetch_new_awards_from_date(last_updated_award_date, get_db)


@app.command()
def fetch_contracts_from_date(from_date: str, until_date: str):
    background_processes.fetcher.fetch_new_awards_from_date(from_date, get_db, until_date)


@app.command()
def remove_dated_application_data():
    """
    Remove dated data from the database.

    This function retrieves applications with a decline, reject, or accepted status that are
    past their due date from the database. It removes sensitive data from these applications
    (e.g., primary_email) and sets the archived_at timestamp to the current UTC time. It also
    removes associated borrower documents.

    If the award associated with the application is not used in any other active applications,
    it will also be deleted from the database. Additionally, if the borrower is not associated
    with any other active applications, their personal information (legal_name, email, address,
    legal_identifier) will be cleared.
    """

    with contextmanager(get_db)() as session:
        dated_applications = application_utils.get_dated_applications(session)
        for application in dated_applications:
            with transaction_session_logger(session, "Error deleting the data"):
                application.award.previous = True
                application.primary_email = ""
                application.archived_at = datetime.utcnow()

                for document in application.borrower_documents:
                    session.delete(document)

                # Check if there are any other active applications that use the same award
                active_applications_with_same_award = (
                    session.query(Application)
                    .filter(
                        Application.award_id == application.award_id,
                        Application.id != application.id,
                        Application.archived_at.is_(None),  # Check that the application is active
                    )
                    .all()
                )
                # Delete the associated Award if no other active applications uses the award
                if len(active_applications_with_same_award) == 0:
                    application.borrower.legal_name = ""
                    application.borrower.email = ""
                    application.borrower.address = ""
                    application.borrower.legal_identifier = ""
                    application.borrower.source_data = ""


@app.command()
def update_applications_to_lapsed():
    """
    Set applications with lapsed status in the database.

    This function retrieves the lapsed applications from the database and updates their status
    to "LAPSED" and sets the application_lapsed_at timestamp to the current UTC time.
    """
    with contextmanager(get_db)() as session:
        lapsed_applications = application_utils.get_lapsed_applications(session)
        for application in lapsed_applications:
            with transaction_session_logger(session, "Error setting to lapsed"):
                application.status = ApplicationStatus.LAPSED
                application.application_lapsed_at = datetime.utcnow()


@app.command()
def send_reminders():
    """
    Send reminders to borrowers.

    This function retrieves applications that require a reminder email to be sent to the borrowers.
    It first retrieves applications that need an introduction reminder and sends the emails. Then,
    it retrieves applications that need a submit reminder and sends those emails as well.

    For each application, it saves the message type (BORROWER_PENDING_APPLICATION_REMINDER or
    BORROWER_PENDING_SUBMIT_REMINDER) to the database and updates the external_message_id after
    the email has been sent successfully.
    """
    applications_to_send_intro_reminder = application_utils.get_applications_to_remind_intro(get_db)
    logger.info("Quantity of mails to send intro reminder " + str(len(applications_to_send_intro_reminder)))
    if len(applications_to_send_intro_reminder) == 0:
        logger.info("No new intro reminder to be sent")
    else:
        for application in applications_to_send_intro_reminder:
            with contextmanager(get_db)() as session:
                with transaction_session_logger(session, "Error sending mail or updating the sent status"):
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

                    messageID = mail.send_mail_intro_reminder(sesClient, uuid, email, borrower_name, buyer_name, title)
                    new_message.external_message_id = messageID
                    logger.info("Mail sent and status updated")

    applications_to_send_submit_reminder = application_utils.get_applications_to_remind_submit(get_db)
    logger.info("Quantity of mails to send submit reminder " + str(len(applications_to_send_submit_reminder)))
    if len(applications_to_send_submit_reminder) == 0:
        logger.info("No new submit reminder to be sent")
    else:
        for application in applications_to_send_submit_reminder:
            with contextmanager(get_db)() as session:
                with transaction_session_logger(session, "Error sending mail or updating the sent status"):
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

                    messageID = mail.send_mail_submit_reminder(
                        sesClient, uuid, email, borrower_name, buyer_name, title
                    )
                    new_message.external_message_id = messageID
                    logger.info("Mail sent and status updated")


@app.command()
def update_statistics():
    background_processes.update_statistic.update_statistics()


@app.command()
def SLA_overdue_applications():
    """
    Send SLA (Service Level Agreement) overdue reminders to borrowers.
    """
    with contextmanager(get_db)() as session:
        applications = application_utils.get_all_applications_with_status(
            [
                core.ApplicationStatus.CONTRACT_UPLOADED,
                core.ApplicationStatus.STARTED,
            ],
            session,
        )
        overdue_lenders = defaultdict(lambda: {"count": 0})
        for application in applications:
            with transaction_session(session):
                days_passed = application_utils.get_application_days_passed(application, session)
                if days_passed > application.lender.sla_days * app_settings.progress_to_remind_started_applications:
                    if "email" not in overdue_lenders[application.lender.id]:
                        overdue_lenders[application.lender.id]["email"] = application.lender.email_group
                        overdue_lenders[application.lender.id]["name"] = application.lender.name
                    overdue_lenders[application.lender.id]["count"] += 1
                    if days_passed > application.lender.sla_days:
                        current_dt = datetime.now(application.created_at.tzinfo)
                        application.overdued_at = current_dt
                        message_id = mail.send_overdue_application_email_to_OCP(
                            sesClient,
                            application.lender.name,
                        )

                        Message.create(
                            session,
                            application=application,
                            type=core.MessageType.OVERDUE_APPLICATION,
                            external_message_id=message_id,
                        )

        for id, lender_data in overdue_lenders.items():
            name = lender_data.get("name")
            count = lender_data.get("count")
            email = lender_data.get("email")
            message_id = mail.send_overdue_application_email_to_FI(sesClient, name, email, count)

            Message.create(
                session,
                application=application,
                type=core.MessageType.OVERDUE_APPLICATION,
                external_message_id=message_id,
            )

        session.commit()


if __name__ == "__main__":
    app()
