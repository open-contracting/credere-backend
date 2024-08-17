from datetime import datetime, timedelta

from typer.testing import CliRunner

from app import commands
from app.settings import app_settings

runner = CliRunner()


def test_send_reminders_intro(session, mock_send_templated_email, pending_application):
    pending_application.expired_at = datetime.now(pending_application.tz) + timedelta(seconds=1)
    session.commit()

    result = runner.invoke(commands.app, ["send-reminders"])

    assert result.exit_code == 0
    assert result.stdout == ""
    assert mock_send_templated_email.call_count == 1


def test_send_reminders_submit(session, mock_send_templated_email, accepted_application):
    accepted_application.borrower_accepted_at = (
        datetime.now(accepted_application.tz)
        - timedelta(days=app_settings.days_to_change_to_lapsed)
        + timedelta(days=app_settings.reminder_days_before_lapsed)
    )
    session.commit()

    result = runner.invoke(commands.app, ["send-reminders"])

    assert result.exit_code == 0
    assert result.stdout == ""
    assert mock_send_templated_email.call_count == 1


def test_send_reminders_no_applications_to_remind(mock_send_templated_email, pending_application):
    result = runner.invoke(commands.app, ["send-reminders"])

    assert result.exit_code == 0
    assert result.stdout == ""
    assert mock_send_templated_email.call_count == 0


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

    result = runner.invoke(commands.app, ["sla-overdue-applications"])

    assert result.exit_code == 0
    assert result.stdout == ""
    assert mock_send_templated_email.call_count == 2


def test_send_overdue_reminders_empty(session, mock_send_templated_email, started_application):
    started_application.lender_started_at = datetime.now(started_application.tz)
    session.commit()

    result = runner.invoke(commands.app, ["sla-overdue-applications"])

    assert result.exit_code == 0
    assert result.stdout == ""
    assert mock_send_templated_email.call_count == 0


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


def test_update_statistic(engine, create_and_drop_database):
    result = runner.invoke(commands.app, ["update-statistics"])

    assert result.exit_code == 0
    assert result.stdout == ""
