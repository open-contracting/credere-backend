import logging
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime

import typer
from sqlalchemy.orm import joinedload

import app.utils.statistics as statistics_utils
from app import mail, models
from app.aws import sesClient
from app.db import get_db, transaction_session, transaction_session_logger
from app.settings import app_settings
from app.utils import background

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
        last_updated_award_date = models.Award.last_updated(session)
    background.fetch_new_awards_from_date(last_updated_award_date, get_db)


@app.command()
def fetch_contracts_from_date(from_date: str, until_date: str):
    background.fetch_new_awards_from_date(from_date, get_db, until_date)


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
        for application in models.Application.archivable(session).options(
            joinedload(models.Application.borrower),
            joinedload(models.Application.borrower_documents),
        ):
            with transaction_session_logger(session, "Error deleting the data"):
                application.award.previous = True
                application.primary_email = ""
                application.archived_at = datetime.utcnow()

                for document in application.borrower_documents:
                    session.delete(document)

                # Check if there are any other active applications that use the same award
                active_applications_with_same_award = (
                    models.Application.unarchived(session)
                    .filter(
                        models.Application.award_id == application.award_id,
                        models.Application.id != application.id,
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
        for application in models.Application.lapsed(session).options(
            joinedload(models.Application.borrower),
            joinedload(models.Application.borrower_documents),
        ):
            with transaction_session_logger(session, "Error setting to lapsed"):
                application.status = models.ApplicationStatus.LAPSED
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
    with contextmanager(get_db)() as session:
        applications_to_send_intro_reminder = (
            models.Application.pending_introduction_reminder(session)
            .options(
                joinedload(models.Application.borrower),
                joinedload(models.Application.award),
            )
            .all()
        )

    length = len(applications_to_send_intro_reminder)
    logger.info("Quantity of mails to send intro reminder %s", length)
    if not length:
        logger.info("No new intro reminder to be sent")
    else:
        for application in applications_to_send_intro_reminder:
            with contextmanager(get_db)() as session:
                with transaction_session_logger(session, "Error sending mail or updating the sent status"):
                    new_message = models.Message.create(
                        session,
                        application=application,
                        type=models.MessageType.BORROWER_PENDING_APPLICATION_REMINDER,
                    )
                    uuid = application.uuid
                    email = application.primary_email
                    borrower_name = application.borrower.legal_name
                    buyer_name = application.award.buyer_name
                    title = application.award.title

                    messageID = mail.send_mail_intro_reminder(sesClient, uuid, email, borrower_name, buyer_name, title)
                    new_message.external_message_id = messageID
                    logger.info("Mail sent and status updated")

    with contextmanager(get_db)() as session:
        applications_to_send_submit_reminder = (
            models.Application.pending_submission_reminder(session)
            .options(
                joinedload(models.Application.borrower),
                joinedload(models.Application.award),
            )
            .all()
        )

    length = len(applications_to_send_submit_reminder)
    logger.info("Quantity of mails to send submit reminder %s", length)
    if not length:
        logger.info("No new submit reminder to be sent")
    else:
        for application in applications_to_send_submit_reminder:
            with contextmanager(get_db)() as session:
                with transaction_session_logger(session, "Error sending mail or updating the sent status"):
                    # Db message table update
                    new_message = models.Message.create(
                        session,
                        application=application,
                        type=models.MessageType.BORROWER_PENDING_SUBMIT_REMINDER,
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
    statistics_utils.update_statistics()


@app.command()
def SLA_overdue_applications():
    """
    Send SLA (Service Level Agreement) overdue reminders to borrowers.
    """
    with contextmanager(get_db)() as session:
        overdue_lenders = defaultdict(lambda: {"count": 0})
        for application in session.query(models.Application).filter(
            models.Application.status.in_(
                [models.ApplicationStatus.CONTRACT_UPLOADED, models.ApplicationStatus.STARTED]
            )
        ):
            with transaction_session(session):
                days_passed = application.days_waiting_for_lender(session)
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

                        models.Message.create(
                            session,
                            application=application,
                            type=models.MessageType.OVERDUE_APPLICATION,
                            external_message_id=message_id,
                        )

        for id, lender_data in overdue_lenders.items():
            name = lender_data.get("name")
            count = lender_data.get("count")
            email = lender_data.get("email")
            message_id = mail.send_overdue_application_email_to_FI(sesClient, name, email, count)

            models.Message.create(
                session,
                application=application,
                type=models.MessageType.OVERDUE_APPLICATION,
                external_message_id=message_id,
            )

        session.commit()


if __name__ == "__main__":
    app()
