from app.commands import remove_dated_application_data
from app.schema import core

from tests.common.common_test_client import start_background_db  # isort:skip # noqa
from tests.common.common_test_client import mock_ses_client  # isort:skip # noqa
from tests.common.common_test_client import mock_cognito_client  # isort:skip # noqa
from tests.common.common_test_client import app, client  # isort:skip # noqa

application_payload = {"status": core.ApplicationStatus.PENDING.value}


def test_remove_data(client):  # noqa
    client.post("/create-test-application", json=application_payload)
    client.get("/set-test-application-as-dated/id/1")
    client.post(
        "/applications/1/update-test-application-status",
        json={"status": core.ApplicationStatus.DECLINED.value},
    )

    remove_dated_application_data()


def test_remove_data_no_dated_application(client):  # noqa
    client.post("/create-test-application", json=application_payload)

    remove_dated_application_data()
