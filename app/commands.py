import logging
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Callable, Generator

import typer
from sqlalchemy.orm import Session, joinedload
from sqlmodel import col

import app.utils.statistics as statistics_utils
from app import mail, models, util
from app.aws import sesClient
from app.db import get_db, handle_skipped_award, rollback_on_error
from app.exceptions import SkippedAwardError
from app.settings import app_settings
from app.sources import colombia as data_access

logger = logging.getLogger(__name__)

app = typer.Typer()


def _create_or_update_borrower_from_data_source(session: Session, entry: dict[str, Any]) -> models.Borrower:
    """
    Create a new borrower or update an existing borrower based on the entry data.

    :param entry: The dictionary containing the borrower data.
    :return: The borrower.
    """
    documento_proveedor = data_access.get_documento_proveedor(entry)
    borrower_identifier = util.get_secret_hash(documento_proveedor)
    data = data_access.get_borrower(borrower_identifier, documento_proveedor, entry)

    borrower = models.Borrower.first_by(session, "borrower_identifier", borrower_identifier)
    if borrower:
        if borrower.status == models.BorrowerStatus.DECLINE_OPPORTUNITIES:
            raise SkippedAwardError(
                "Borrower opted to not receive any new opportunity",
                data={"borrower_identifier": borrower_identifier},
            )
        return borrower.update(session, **data)

    return models.Borrower.create(session, **data)


def _create_application(
    session: Session,
    award_id: int | None,
    borrower_id: int | None,
    email: str,
    legal_identifier: str,
    source_contract_id: str,
) -> models.Application:
    """
    Create a new application and insert it into the database.

    :param award_id: The ID of the award associated with the application.
    :param borrower_id: The ID of the borrower associated with the application.
    :param email: The email of the borrower.
    :param legal_identifier: The legal identifier of the borrower.
    :param source_contract_id: The ID of the source contract.
    :return: The created application.
    """
    award_borrower_identifier: str = util.get_secret_hash(f"{legal_identifier}{source_contract_id}")

    application = models.Application.first_by(session, "award_borrower_identifier", award_borrower_identifier)
    if application:
        raise SkippedAwardError(
            "Application already exists",
            data={
                "found": application.id,
                "lookup": {"legal_identifier": legal_identifier, "sources_contract_id": source_contract_id},
            },
        )

    new_uuid: str = util.generate_uuid(award_borrower_identifier)
    data = {
        "award_id": award_id,
        "borrower_id": borrower_id,
        "primary_email": email,
        "award_borrower_identifier": award_borrower_identifier,
        "uuid": new_uuid,
        "expired_at": datetime.utcnow() + timedelta(days=app_settings.application_expiration_days),
    }

    return models.Application.create(session, **data)


def _create_complete_application(award_response, db_provider: Callable[[], Generator[Session, None, None]]) -> None:
    with contextmanager(db_provider)() as session:
        with handle_skipped_award(session, "Error creating application"):
            award = util.create_award_from_data_source(session, award_response)
            borrower = _create_or_update_borrower_from_data_source(session, award_response)
            award.borrower_id = borrower.id

            application = _create_application(
                session,
                award.id,
                borrower.id,
                borrower.email,
                borrower.legal_identifier,
                award.source_contract_id,
            )

            message = models.Message.create(
                session,
                application=application,
                type=models.MessageType.BORROWER_INVITATION,
            )

            message_id = mail.send_invitation_email(
                sesClient,
                application.uuid,
                borrower.email,
                borrower.legal_name,
                award.buyer_name,
                award.title,
            )
            message.external_message_id = message_id

            session.commit()


def _get_awards_from_data_source(
    last_updated_award_date: datetime,
    db_provider: Callable[[], Generator[Session, None, None]],
    until_date: datetime | None = None,
) -> None:
    """
    Fetch new awards from the given date and process them.

    :param last_updated_award_date: Date string in the format 'YYYY-MM-DD'.
    :type last_updated_award_date: datetime
    """
    index = 0
    awards_response = data_access.get_new_awards(index, last_updated_award_date, until_date)
    awards_response_json = awards_response.json()

    if not awards_response_json:
        logger.info("No new contracts")
        return
    total = 0
    while awards_response_json:
        total += len(awards_response_json)
        for entry in awards_response_json:
            if not all(key in entry for key in ("id_del_portafolio", "nit_del_proveedor_adjudicado")):
                raise SkippedAwardError(
                    "Source contract is missing required fields",
                    url=awards_response.url,
                    data={"response": awards_response_json},
                )
            _create_complete_application(entry, db_provider)
        index += 1
        awards_response = data_access.get_new_awards(index, last_updated_award_date, until_date)
        awards_response_json = awards_response.json()
    logger.info("Total fetched contracts: %d", total)


@app.command()
def fetch_awards() -> None:
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
    _get_awards_from_data_source(last_updated_award_date, get_db)


@app.command()
def fetch_all_awards_from_period(from_date: datetime, until_date: datetime) -> None:
    """
    NOTE: For manual use only.
    Fetch all awards, regardless of their status, from the from_date, until_date period.
    Useful when want to force send invitations for awards made in the past.
    """
    _get_awards_from_data_source(from_date, get_db, until_date)


@app.command()
def fetch_award_by_id_and_supplier(award_id: str, supplier_id: str) -> None:
    """
    NOTE: For manual use only.
    Fetch a specific award by award_id and supplier_id.
    Useful when want to directly invite a supplier who for some reason wasn't invited by Credere.
    """
    award_response = data_access.get_award_by_id_and_supplier(award_id, supplier_id).json()
    if not award_response:
        logger.info(f"The award with id {award_id} and supplier id {supplier_id} was not found")
        return
    _create_complete_application(award_response[0], get_db)


@app.command()
def remove_dated_application_data() -> None:
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
            with rollback_on_error(session):
                application.award.previous = True
                application.primary_email = ""
                application.archived_at = datetime.utcnow()

                for document in application.borrower_documents:
                    session.delete(document)

                # Check if the borrower has other active applications
                active_applications_with_same_borrower = (
                    models.Application.unarchived(session)
                    .filter(
                        models.Application.borrower_id == application.borrower_id,
                        models.Application.id != application.id,
                    )
                    .all()
                )
                # Delete the associated borrower info if no other active applications uses the borrower
                if len(active_applications_with_same_borrower) == 0:
                    application.borrower.legal_name = ""
                    application.borrower.email = ""
                    application.borrower.address = ""
                    application.borrower.legal_identifier = ""
                    application.borrower.source_data = {}

                session.commit()


@app.command()
def update_applications_to_lapsed() -> None:
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
            with rollback_on_error(session):
                application.status = models.ApplicationStatus.LAPSED
                application.application_lapsed_at = datetime.utcnow()

                session.commit()


@app.command()
def send_reminders() -> None:
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
                with rollback_on_error(session):
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

                    message_id = mail.send_mail_intro_reminder(
                        sesClient, uuid, email, borrower_name, buyer_name, title
                    )
                    new_message.external_message_id = message_id
                    logger.info("Mail sent and status updated")

                    session.commit()

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
                with rollback_on_error(session):
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

                    message_id = mail.send_mail_submit_reminder(
                        sesClient, uuid, email, borrower_name, buyer_name, title
                    )
                    new_message.external_message_id = message_id
                    logger.info("Mail sent and status updated")

                    session.commit()


@app.command()
def update_statistics() -> None:
    statistics_utils.update_statistics()


@app.command()
def sla_overdue_applications() -> None:
    """
    Send SLA (Service Level Agreement) overdue reminders to borrowers.
    """
    with contextmanager(get_db)() as session:
        overdue_lenders: dict[str, Any] = defaultdict(lambda: {"count": 0})
        for application in session.query(models.Application).filter(
            col(models.Application.status).in_(
                [models.ApplicationStatus.CONTRACT_UPLOADED, models.ApplicationStatus.STARTED]
            )
        ):
            with rollback_on_error(session):
                days_passed = application.days_waiting_for_lender(session)
                if days_passed > application.lender.sla_days * app_settings.progress_to_remind_started_applications:
                    if "email" not in overdue_lenders[application.lender.id]:
                        overdue_lenders[application.lender.id]["email"] = application.lender.email_group
                        overdue_lenders[application.lender.id]["name"] = application.lender.name
                    overdue_lenders[application.lender.id]["count"] += 1
                    if days_passed > application.lender.sla_days:
                        current_dt = datetime.now(application.created_at.tzinfo)
                        application.overdued_at = current_dt
                        message_id = mail.send_overdue_application_email_to_ocp(
                            sesClient,
                            application.lender.name,
                        )

                        models.Message.create(
                            session,
                            application=application,
                            type=models.MessageType.OVERDUE_APPLICATION,
                            external_message_id=message_id,
                        )

                session.commit()

        for lender_id, lender_data in overdue_lenders.items():
            name = lender_data["name"]
            count = lender_data["count"]
            email = lender_data["email"]
            message_id = mail.send_overdue_application_email_to_fi(sesClient, name, email, count)

            models.Message.create(
                session,
                application=application,
                type=models.MessageType.OVERDUE_APPLICATION,
                external_message_id=message_id,
            )

        session.commit()


if __name__ == "__main__":
    app()
