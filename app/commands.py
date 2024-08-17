import json
import logging
import sys
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Callable, Generator

import click
import minify_html
import typer
import typer.cli
from sqlalchemy import Date, cast
from sqlalchemy.orm import Session, joinedload
from sqlmodel import col

import app.utils.statistics as statistics_utils
from app import aws, mail, models, util
from app.db import get_db, handle_skipped_award, rollback_on_error
from app.exceptions import SkippedAwardError, SourceFormatError
from app.settings import app_settings
from app.sources import colombia as data_access

logger = logging.getLogger(__name__)


class OrderedGroup(typer.cli.TyperCLIGroup):
    # https://github.com/fastapi/typer/blob/adca3254f8c2adc8d9b71b5cdea65c41770bd9b9/typer/cli.py#L55-L57
    # https://github.com/pallets/click/blob/e16088a8569597c55f108ea89af6245898249ec2/src/click/core.py#L1684-L1686
    def list_commands(self, ctx: click.Context) -> list[str]:
        self.maybe_add_run(ctx)
        return list(self.commands)


app = typer.Typer(cls=OrderedGroup)
dev = typer.Typer()
app.add_typer(dev, name="dev", help="Commands for maintainers of Credere.")


# Called by fetch-award* commands.
def _create_complete_application(
    award_entry: dict[str, str], db_provider: Callable[[], Generator[Session, None, None]]
) -> None:
    with contextmanager(db_provider)() as session:
        with handle_skipped_award(session, "Error creating application"):
            # Create the award. If it exists, skip this award.
            award = util.create_award_from_data_source(session, award_entry)

            # Create a new borrower or update an existing borrower based on the entry data.
            documento_proveedor = data_access.get_documento_proveedor(award_entry)
            borrower_identifier = util.get_secret_hash(documento_proveedor)
            data = data_access.get_borrower(borrower_identifier, documento_proveedor, award_entry)
            if borrower := models.Borrower.first_by(session, "borrower_identifier", borrower_identifier):
                if borrower.status == models.BorrowerStatus.DECLINE_OPPORTUNITIES:
                    raise SkippedAwardError(
                        "Borrower opted to not receive any new opportunity",
                        data={"borrower_identifier": borrower_identifier},
                    )
                borrower = borrower.update(session, **data)
            else:
                borrower = models.Borrower.create(session, **data)

            award.borrower = borrower

            # Create a new application and insert it into the database.
            award_borrower_identifier: str = util.get_secret_hash(
                f"{borrower.legal_identifier}{award.source_contract_id}"
            )
            if application := models.Application.first_by(
                session, "award_borrower_identifier", award_borrower_identifier
            ):
                raise SkippedAwardError(
                    "Application already exists",
                    data={
                        "found": application.id,
                        "lookup": {
                            "legal_identifier": borrower.legal_identifier,
                            "sources_contract_id": award.source_contract_id,
                        },
                    },
                )
            application = models.Application.create(
                session,
                award=award,
                borrower=borrower,
                primary_email=borrower.email,
                award_borrower_identifier=award_borrower_identifier,
                uuid=util.generate_uuid(award_borrower_identifier),
                expired_at=datetime.utcnow() + timedelta(days=app_settings.application_expiration_days),
            )

            message_id = mail.send_invitation_email(aws.ses_client, application)
            models.Message.create(
                session,
                application=application,
                type=models.MessageType.BORROWER_INVITATION,
                external_message_id=message_id,
            )

            session.commit()


@app.command()
def fetch_awards(
    from_date: datetime = typer.Option(default=None, formats=["%Y-%m-%d"]),
    until_date: datetime = typer.Option(default=None, formats=["%Y-%m-%d"]),
) -> None:
    """
    Fetch new awards from the date of the most recently updated award, or in the period described by the --from-date
    and --until-date options.

    \b
    -  If the award already exists, skip the award.
       Otherwise, create the award.
    -  If the borrower opted out of Credere entirely, skip the award.
       Otherwise, create or update the borrower.
    -  If the application already exists, skip the award.
       Otherwise, create a PENDING application and email an invitation to the borrower.
    """

    if bool(from_date) ^ bool(until_date):
        raise click.UsageError("--from-date and --until-date must either be both set or both not set.")
    if from_date and until_date and from_date > until_date:
        raise click.UsageError("--from-date must be earlier than --until-date.")

    if from_date is None:
        with contextmanager(get_db)() as session:
            from_date = models.Award.last_updated(session)

    index = 0
    awards_response = data_access.get_new_awards(index, from_date, until_date)
    awards_response_json = util.loads(awards_response)

    if not awards_response_json:
        logger.info("No new contracts")
        return

    total = 0
    while awards_response_json:
        total += len(awards_response_json)

        for entry in awards_response_json:
            if not all(key in entry for key in ("id_del_portafolio", "nit_del_proveedor_adjudicado")):
                raise SourceFormatError(
                    "Source contract is missing required fields:"
                    f" url={awards_response.url}, data={awards_response_json}"
                )
            _create_complete_application(entry, get_db)

        index += 1
        awards_response = data_access.get_new_awards(index, from_date, until_date)
        awards_response_json = util.loads(awards_response)

    logger.info("Total fetched contracts: %d", total)


@app.command()
def fetch_award_by_id_and_supplier(award_id: str, supplier_id: str) -> None:
    """
    Fetch one award, by award ID and supplier ID, and process it like the fetch-awards command.
    Use this to manually invite a borrower who wasn't automatically invited.
    """
    award_response_json = util.loads(data_access.get_award_by_id_and_supplier(award_id, supplier_id))
    if not award_response_json:
        logger.info(f"The award with id {award_id} and supplier id {supplier_id} was not found")
        return
    _create_complete_application(award_response_json[0], get_db)


@app.command()
def send_reminders() -> None:
    """
    Send reminders to borrowers about PENDING and ACCEPTED applications.
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
                    message_id = mail.send_mail_intro_reminder(aws.ses_client, application)
                    models.Message.create(
                        session,
                        application=application,
                        type=models.MessageType.BORROWER_PENDING_APPLICATION_REMINDER,
                        external_message_id=message_id,
                    )

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
                    message_id = mail.send_mail_submit_reminder(aws.ses_client, application)
                    models.Message.create(
                        session,
                        application=application,
                        type=models.MessageType.BORROWER_PENDING_SUBMIT_REMINDER,
                        external_message_id=message_id,
                    )

                    logger.info("Mail sent and status updated")

                    session.commit()


@app.command()
def update_applications_to_lapsed() -> None:
    """
    Lapse applications that have been waiting for the borrower to respond for some time.
    """
    with contextmanager(get_db)() as session:
        for application in models.Application.lapseable(session).options(
            joinedload(models.Application.borrower),
            joinedload(models.Application.borrower_documents),
        ):
            with rollback_on_error(session):
                application.status = models.ApplicationStatus.LAPSED
                application.application_lapsed_at = datetime.utcnow()

                session.commit()


@app.command()
def update_statistics() -> None:
    """
    Update and store various statistics related to applications and lenders in the database.
    """
    keys_to_serialize = [
        "sector_statistics",
        "rejected_reasons_count_by_reason",
        "fis_chosen_by_supplier",
    ]

    with contextmanager(get_db)() as session:
        with rollback_on_error(session):
            # Get general KPIs
            statistic_kpis = statistics_utils.get_general_statistics(session, None, None, None)

            models.Statistic.create_or_update(
                session,
                [
                    cast(col(models.Statistic.created_at), Date) == datetime.today().date(),
                    models.Statistic.type == models.StatisticType.APPLICATION_KPIS,
                ],
                type=models.StatisticType.APPLICATION_KPIS,
                data=statistic_kpis,
            )

            # Get opt-in statistics
            statistics_opt_in = statistics_utils.get_borrower_opt_in_stats(session)
            for key in keys_to_serialize:
                statistics_opt_in[key] = [data.model_dump() for data in statistics_opt_in[key]]

            models.Statistic.create_or_update(
                session,
                [
                    cast(col(models.Statistic.created_at), Date) == datetime.today().date(),
                    models.Statistic.type == models.StatisticType.MSME_OPT_IN_STATISTICS,
                ],
                type=models.StatisticType.MSME_OPT_IN_STATISTICS,
                data=statistics_opt_in,
            )

            # Get general KPIs for every lender
            for (lender_id,) in session.query(models.Lender.id):
                # Get statistics for each lender
                statistic_kpis = statistics_utils.get_general_statistics(session, None, None, lender_id)

                models.Statistic.create_or_update(
                    session,
                    [
                        cast(col(models.Statistic.created_at), Date) == datetime.today().date(),
                        models.Statistic.type == models.StatisticType.APPLICATION_KPIS,
                        models.Statistic.lender_id == lender_id,
                    ],
                    type=models.StatisticType.APPLICATION_KPIS,
                    data=statistic_kpis,
                    lender_id=lender_id,
                )

            session.commit()


@app.command()
def sla_overdue_applications() -> None:
    """
    Send reminders to lenders and OCP about overdue applications.
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
                        application.overdued_at = datetime.now(application.created_at.tzinfo)

                        message_id = mail.send_overdue_application_email_to_ocp(
                            aws.ses_client, application.lender.name
                        )
                        models.Message.create(
                            session,
                            application=application,
                            type=models.MessageType.OVERDUE_APPLICATION,
                            external_message_id=message_id,
                        )

                session.commit()

        for lender_id, lender_data in overdue_lenders.items():
            message_id = mail.send_overdue_application_email_to_lender(
                aws.ses_client, lender_data["name"], lender_data["count"], lender_data["email"]
            )
            models.Message.create(
                session,
                # NOTE: A random application that might not even be to the lender, but application is not nullable.
                application=application,
                type=models.MessageType.OVERDUE_APPLICATION,
                external_message_id=message_id,
            )

        session.commit()


@app.command()
def remove_dated_application_data() -> None:
    """
    Clear personal data and delete borrower documents from applications that have been in a final state for some time.
    If the borrower has no other active applications, clear the borrower's personal data.
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

                # Clear the associated borrower's personal data if they have no other active applications.
                if not session.query(
                    models.Application.unarchived(session)
                    .filter(
                        models.Application.borrower_id == application.borrower_id,
                        models.Application.id != application.id,
                    )
                    .exists()
                ).scalar():
                    application.borrower.legal_name = ""
                    application.borrower.email = ""
                    application.borrower.address = ""
                    application.borrower.legal_identifier = ""
                    application.borrower.source_data = {}

                session.commit()


@dev.command()
def cli_input_json(name: str, file: typer.FileText) -> None:
    """
    Print a JSON string for the aws ses create-template --cli-input-json argument.
    """
    # aws ses create-template --generate-cli-skeleton
    json.dump(
        {
            "Template": {
                "TemplateName": name,
                "Subject": "{{SUBJECT}}",
                "HtmlPart": minify_html.minify(
                    file.read(),
                    do_not_minify_doctype=True,
                    ensure_spec_compliant_unquoted_attribute_values=True,
                    keep_spaces_between_attributes=True,
                    minify_css=True,
                ),
            }
        },
        sys.stdout,
        indent=4,
        ensure_ascii=False,
    )


if __name__ == "__main__":
    app()
