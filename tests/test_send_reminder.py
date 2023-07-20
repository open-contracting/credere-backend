from app.background_processes.send_reminder import send_reminders
from app.schema import core
from tests.common import common_test_client

from tests.common.common_test_client import start_background_db  # isort:skip # noqa
from tests.common.common_test_client import mock_ses_client  # isort:skip # noqa
from tests.common.common_test_client import mock_cognito_client  # isort:skip # noqa
from tests.common.common_test_client import app, client  # isort:skip # noqa

application_payload = {"status": core.ApplicationStatus.PENDING.value}
application_accepted_payload = {"status": core.ApplicationStatus.ACCEPTED.value}


def test_send_reminders_intro(client):  # noqa
    client.post("/create-test-application", json=application_payload)
    client.get("/set-test-application-to-remind/id/1")
    send_reminders(common_test_client.get_test_db)


def test_send_reminders_submit(client):  # noqa
    client.post("/create-test-application", json=application_accepted_payload)
    client.get("/set-test-application-to-remind/id/1")
    send_reminders(common_test_client.get_test_db)


def test_send_reminders_no_applications_to_remind(client):  # noqa
    client.post("/create-test-application", json=application_payload)
    send_reminders(common_test_client.get_test_db)
