from app import models
from app.commands import update_applications_to_lapsed

from tests.common.common_test_client import start_background_db  # isort:skip # noqa
from tests.common.common_test_client import mock_ses_client  # isort:skip # noqa
from tests.common.common_test_client import mock_cognito_client  # isort:skip # noqa
from tests.common.common_test_client import app, client  # isort:skip # noqa

application_payload = {"status": models.ApplicationStatus.PENDING.value}


def test_set_lapsed_applications(client):  # noqa
    client.post("/create-test-application", json=application_payload)
    client.get("/set-test-application-as-lapsed/id/1")
    update_applications_to_lapsed()


def test_set_lapsed_applications_no_lapsed(client):  # noqa
    client.post("/create-test-application", json=application_payload)
    update_applications_to_lapsed()
