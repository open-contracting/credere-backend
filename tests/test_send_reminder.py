from app import models
from app.commands import send_reminders

from tests.common.common_test_client import start_background_db  # isort:skip # noqa
from tests.common.common_test_client import mock_templated_email  # isort:skip # noqa
from tests.common.common_test_client import mock_ses_client  # isort:skip # noqa
from tests.common.common_test_client import mock_cognito_client  # isort:skip # noqa
from tests.common.common_test_client import app, client  # isort:skip # noqa

application_payload = {"status": models.ApplicationStatus.PENDING}
application_accepted_payload = {"status": models.ApplicationStatus.ACCEPTED}


def test_send_reminders_intro(client, mock_templated_email):  # noqa
    client.post("/create-test-application", json=application_payload)
    client.get("/set-test-application-to-remind/id/1")
    send_reminders()
    assert mock_templated_email.call_count == 1


def test_send_reminders_submit(client, mock_templated_email):  # noqa
    client.post("/create-test-application", json=application_accepted_payload)
    client.get("/set-test-application-to-remind/id/1")
    send_reminders()
    assert mock_templated_email.call_count == 1


def test_send_reminders_no_applications_to_remind(client, mock_templated_email):  # noqa
    client.post("/create-test-application", json=application_payload)
    send_reminders()
    assert mock_templated_email.call_count == 0
