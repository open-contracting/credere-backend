from app.background_processes import lapsed_applications
from app.schema import core
from tests.common import common_test_client

from tests.common.common_test_client import start_background_db  # isort:skip # noqa
from tests.common.common_test_client import mock_ses_client  # isort:skip # noqa
from tests.common.common_test_client import mock_cognito_client  # isort:skip # noqa
from tests.common.common_test_client import app, client  # isort:skip # noqa

application_payload = {"status": core.ApplicationStatus.PENDING.value}


def test_set_lapsed_applications(client):  # noqa
    client.post("/create-test-application", json=application_payload)
    client.get("/set-test-application-as-lapsed/id/1")
    lapsed_applications.set_lapsed_applications(common_test_client.get_test_db)


def test_set_lapsed_applications_no_lapsed(client):  # noqa
    client.post("/create-test-application", json=application_payload)
    lapsed_applications.set_lapsed_applications(common_test_client.get_test_db)
