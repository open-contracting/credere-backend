from app import models
from app.commands import SLA_overdue_applications

OCP_user = {
    "email": "OCP_user@example.com",
    "name": "OCP_user@example.com",
    "type": models.UserType.OCP,
}

application = {"status": models.ApplicationStatus.STARTED}

application_with_lender_payload = {
    "status": models.ApplicationStatus.STARTED,
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


def test_send_overdue_reminders(client, mock_templated_email):
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    client.post("/lenders", json=lender, headers=OCP_headers)
    client.post("/create-test-application", json=application_with_lender_payload)

    client.get("/set-application-as-overdue/id/1")
    SLA_overdue_applications()
    assert mock_templated_email.call_count == 2


def test_send_overdue_reminders_empty(client, mock_templated_email):
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    client.post("/lenders", json=lender, headers=OCP_headers)
    client.post("/create-test-application", json=application_with_lender_payload)
    client.get("/set-application-as-started/id/1")
    SLA_overdue_applications()
    assert mock_templated_email.call_count == 0
