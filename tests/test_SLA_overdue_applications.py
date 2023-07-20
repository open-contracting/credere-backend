import pytest
from app.background_processes import SLA_overdue_applications
from app.schema import core
from tests.common import common_test_client


from tests.common.common_test_client import start_background_db  # isort:skip # noqa
from tests.common.common_test_client import mock_templated_email  # isort:skip # noqa
from tests.common.common_test_client import mock_ses_client  # isort:skip # noqa
from tests.common.common_test_client import mock_cognito_client  # isort:skip # noqa
from tests.common.common_test_client import app, client  # isort:skip # noqa

OCP_user = {
    "email": "OCP_user@example.com",
    "name": "OCP_user@example.com",
    "type": core.UserType.OCP.value,
}

application = {"status": core.ApplicationStatus.STARTED.value}

application_with_lender_payload = {
    "status": core.ApplicationStatus.STARTED.value,
    "lender_id": 1,
}
lender = {
    "id": 1,
    "name": "test",
    "email_group": "test@lender.com",
    "status": "Active",
    "type": "Some Type",
    "sla_days": 7,
}


def test_send_overdue_reminders(client, mock_templated_email):  # noqa
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    client.post("/lenders", json=lender, headers=OCP_headers)
    client.post("/create-test-application", json=application_with_lender_payload)

    client.get("/set-application-as-overdue/id/1")
    SLA_overdue_applications.SLA_overdue_applications(common_test_client.get_test_db)
    assert mock_templated_email.call_count == 2


def test_send_overdue_reminders_empty(client, mock_templated_email):  # noqa
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    client.post("/lenders", json=lender, headers=OCP_headers)
    client.post("/create-test-application", json=application_with_lender_payload)
    client.get("/set-application-as-started/id/1")
    SLA_overdue_applications.SLA_overdue_applications(common_test_client.get_test_db)
    assert mock_templated_email.call_count == 0
