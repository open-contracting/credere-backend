from datetime import datetime, timedelta

import pytest
from typer.testing import CliRunner

from app import __main__, models
from app.settings import app_settings
from tests import assert_change, assert_success

runner = CliRunner()
# Do 1-2 seconds off the minimum offset, to avoid test failures due to timing issues.
negative_offset = -5  # min 0
positive_offset = 5  # min 1


@pytest.mark.parametrize(
    ("seconds", "call_count"),
    [
        (negative_offset, 0),
        (positive_offset, 1),
        (app_settings.reminder_days_before_expiration * 86_400 + negative_offset, 1),
        (app_settings.reminder_days_before_expiration * 86_400 + positive_offset, 0),
    ],
)
def test_send_reminders_intro(session, mock_send_templated_email, pending_application, seconds, call_count):
    pending_application.expired_at = datetime.now(pending_application.tz) + timedelta(seconds=seconds)
    session.commit()

    with assert_change(mock_send_templated_email, "call_count", call_count):
        result = runner.invoke(__main__.app, ["send-reminders"])

        assert_success(
            result,
            f"Sending {call_count} BORROWER_PENDING_APPLICATION_REMINDER...\n"
            "Sending 0 BORROWER_PENDING_SUBMIT_REMINDER...\n"
            "Sending 0 BORROWER_PENDING_EXTERNAL_ONBOARDING_REMINDER...\n",
        )

    # If run a second time, reminder is not sent.
    with assert_change(mock_send_templated_email, "call_count", 0):
        result = runner.invoke(__main__.app, ["send-reminders"])

        assert_success(
            result,
            "Sending 0 BORROWER_PENDING_APPLICATION_REMINDER...\n"
            "Sending 0 BORROWER_PENDING_SUBMIT_REMINDER...\n"
            "Sending 0 BORROWER_PENDING_EXTERNAL_ONBOARDING_REMINDER...\n",
        )


@pytest.mark.parametrize(
    ("seconds", "call_count"),
    [
        (negative_offset, 0),
        (positive_offset, 1),
        (app_settings.reminder_days_before_lapsed * 86_400 + negative_offset, 1),
        (app_settings.reminder_days_before_lapsed * 86_400 + positive_offset, 0),
    ],
)
def test_send_reminders_submit(session, mock_send_templated_email, accepted_application, seconds, call_count):
    accepted_application.borrower_accepted_at = (
        datetime.now(accepted_application.tz)
        - timedelta(days=app_settings.days_to_change_to_lapsed)
        + timedelta(seconds=seconds)
    )
    session.commit()

    with assert_change(mock_send_templated_email, "call_count", call_count):
        result = runner.invoke(__main__.app, ["send-reminders"])

        assert_success(
            result,
            "Sending 0 BORROWER_PENDING_APPLICATION_REMINDER...\n"
            f"Sending {call_count} BORROWER_PENDING_SUBMIT_REMINDER...\n"
            "Sending 0 BORROWER_PENDING_EXTERNAL_ONBOARDING_REMINDER...\n",
        )

    # If run a second time, reminder is not sent.
    with assert_change(mock_send_templated_email, "call_count", 0):
        result = runner.invoke(__main__.app, ["send-reminders"])

        assert_success(
            result,
            "Sending 0 BORROWER_PENDING_APPLICATION_REMINDER...\n"
            "Sending 0 BORROWER_PENDING_SUBMIT_REMINDER...\n"
            "Sending 0 BORROWER_PENDING_EXTERNAL_ONBOARDING_REMINDER...\n",
        )


def test_send_reminders_external_onboarding(session, mock_send_templated_email, accepted_application, lender):
    call_count = 1
    accepted_application.status = models.ApplicationStatus.SUBMITTED
    accepted_application.borrower_submitted_at = datetime.now(accepted_application.created_at.tzinfo)
    lender.external_onboarding_url = "https://example.com"
    accepted_application.lender = lender
    session.commit()

    with assert_change(mock_send_templated_email, "call_count", call_count):
        result = runner.invoke(__main__.app, ["send-reminders"])

        assert_success(
            result,
            "Sending 0 BORROWER_PENDING_APPLICATION_REMINDER...\n"
            "Sending 0 BORROWER_PENDING_SUBMIT_REMINDER...\n"
            f"Sending {call_count} BORROWER_PENDING_EXTERNAL_ONBOARDING_REMINDER...\n",
        )

    # If run a second time, reminder is not sent.
    with assert_change(mock_send_templated_email, "call_count", 0):
        result = runner.invoke(__main__.app, ["send-reminders"])

        assert_success(
            result,
            "Sending 0 BORROWER_PENDING_APPLICATION_REMINDER...\n"
            "Sending 0 BORROWER_PENDING_SUBMIT_REMINDER...\n"
            "Sending 0 BORROWER_PENDING_EXTERNAL_ONBOARDING_REMINDER...\n",
        )


@pytest.mark.parametrize(("seconds", "lapsed"), [(negative_offset, True), (positive_offset, False)])
def test_set_lapsed_applications(session, pending_application, seconds, lapsed):
    pending_application.created_at = (
        datetime.now(pending_application.tz)
        - timedelta(days=app_settings.days_to_change_to_lapsed)
        + timedelta(seconds=seconds)
    )
    session.commit()

    result = runner.invoke(__main__.app, ["update-applications-to-lapsed"])
    session.expire_all()

    assert_success(result)
    assert (pending_application.status == models.ApplicationStatus.LAPSED) == lapsed
    assert (pending_application.application_lapsed_at is not None) == lapsed


def test_set_lapsed_applications_no_lapsed(session, pending_application):
    result = runner.invoke(__main__.app, ["update-applications-to-lapsed"])
    session.expire_all()

    assert_success(result)
    assert pending_application.status == models.ApplicationStatus.PENDING
    assert pending_application.application_lapsed_at is None


@pytest.mark.parametrize(
    ("seconds", "call_count", "overdue"),
    [
        (4 * 86_400, 0, False),
        (5 * 86_400, 1, False),
        (7 * 86_400, 1, False),
        (8 * 86_400, 2, True),
    ],
)
def test_send_overdue_reminders(
    reset_database,
    session,
    mock_send_templated_email,
    started_application,
    lender_header,
    seconds,
    call_count,
    overdue,
):
    started_application.lender_started_at = datetime.now(started_application.tz) - timedelta(seconds=seconds)
    session.commit()

    with assert_change(mock_send_templated_email, "call_count", call_count):
        result = runner.invoke(__main__.app, ["sla-overdue-applications"])
        session.expire_all()

        assert_success(result)
        assert (started_application.overdued_at is not None) == overdue


def test_remove_data(session, declined_application):
    declined_application.borrower_declined_at = datetime.now(declined_application.tz) - timedelta(
        days=app_settings.days_to_erase_borrowers_data + 1
    )
    session.commit()

    result = runner.invoke(__main__.app, ["remove-dated-application-data"])
    session.expire_all()

    assert_success(result)
    assert declined_application.award.previous is True
    assert declined_application.primary_email == ""
    assert declined_application.archived_at is not None
    assert declined_application.borrower_documents == []
    assert declined_application.borrower.legal_name == ""
    assert declined_application.borrower.email == ""
    assert declined_application.borrower.address == ""
    assert declined_application.borrower.legal_identifier == ""
    assert declined_application.borrower.source_data == {}


def test_remove_data_no_dated_application(session, pending_application):
    result = runner.invoke(__main__.app, ["remove-dated-application-data"])
    session.expire_all()

    assert_success(result)
    assert pending_application.award.previous is False
    assert pending_application.primary_email != ""
    assert pending_application.archived_at is None
    # documents and legal_name are empty, like in the fixture.
    assert pending_application.borrower.email != ""
    assert pending_application.borrower.address != ""
    assert pending_application.borrower.legal_identifier != ""
    assert pending_application.borrower.source_data != {}
