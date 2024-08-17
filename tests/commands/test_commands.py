from datetime import datetime, timedelta

from typer.testing import CliRunner

from app import commands, models
from app.settings import app_settings
from tests import assert_change

runner = CliRunner()


def test_send_reminders_intro(session, mock_send_templated_email, pending_application):
    pending_application.expired_at = datetime.now(pending_application.tz) + timedelta(seconds=1)
    session.commit()

    with assert_change(mock_send_templated_email, "call_count", 1):
        result = runner.invoke(commands.app, ["send-reminders"])

    assert result.exit_code == 0
    assert result.stdout == ""


def test_send_reminders_submit(session, mock_send_templated_email, accepted_application):
    accepted_application.borrower_accepted_at = (
        datetime.now(accepted_application.tz)
        - timedelta(days=app_settings.days_to_change_to_lapsed)
        + timedelta(days=app_settings.reminder_days_before_lapsed)
    )
    session.commit()

    with assert_change(mock_send_templated_email, "call_count", 1):
        result = runner.invoke(commands.app, ["send-reminders"])

    assert result.exit_code == 0
    assert result.stdout == ""


def test_send_reminders_no_applications_to_remind(mock_send_templated_email, pending_application):
    with assert_change(mock_send_templated_email, "call_count", 0):
        result = runner.invoke(commands.app, ["send-reminders"])

    assert result.exit_code == 0
    assert result.stdout == ""


def test_set_lapsed_applications(session, pending_application):
    pending_application.created_at = datetime.now(pending_application.tz) - timedelta(
        days=app_settings.days_to_change_to_lapsed + 2
    )
    session.commit()

    result = runner.invoke(commands.app, ["update-applications-to-lapsed"])

    assert result.exit_code == 0
    assert result.stdout == ""


def test_set_lapsed_applications_no_lapsed(pending_application):
    result = runner.invoke(commands.app, ["update-applications-to-lapsed"])

    assert result.exit_code == 0
    assert result.stdout == ""


def test_send_overdue_reminders(session, mock_send_templated_email, started_application):
    started_application.lender_started_at = datetime.now(started_application.tz) - timedelta(
        days=started_application.lender.sla_days + 1
    )
    session.commit()

    with assert_change(mock_send_templated_email, "call_count", 2):  # to admin and lender
        result = runner.invoke(commands.app, ["sla-overdue-applications"])

    assert result.exit_code == 0
    assert result.stdout == ""


def test_send_overdue_reminders_empty(session, mock_send_templated_email, started_application):
    # Lapse all applications already in the database.
    session.query(models.Application).filter(models.Application.id != started_application.id).update(
        {"status": models.ApplicationStatus.LAPSED}
    )

    started_application.lender_started_at = datetime.now(started_application.tz)
    session.commit()

    with assert_change(mock_send_templated_email, "call_count", 0):
        result = runner.invoke(commands.app, ["sla-overdue-applications"])

    assert result.exit_code == 0
    assert result.stdout == ""


def test_remove_data(session, declined_application):
    declined_application.borrower_declined_at = datetime.now(declined_application.tz) - timedelta(
        days=app_settings.days_to_erase_borrowers_data + 1
    )
    session.commit()

    result = runner.invoke(commands.app, ["remove-dated-application-data"])

    assert result.exit_code == 0
    assert result.stdout == ""


def test_remove_data_no_dated_application(pending_application):
    result = runner.invoke(commands.app, ["remove-dated-application-data"])

    assert result.exit_code == 0
    assert result.stdout == ""


def test_update_statistic(engine):
    result = runner.invoke(commands.app, ["update-statistics"])

    assert result.exit_code == 0
    assert result.stdout == ""
