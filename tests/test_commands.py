from fastapi import status
from typer.testing import CliRunner

from app import commands, models

ocp_user = {
    "email": "OCP-user@example.com",
    "name": "OCP-user@example.com",
    "type": models.UserType.OCP,
}
lender = {
    "id": 1,
    "name": "test",
    "email_group": "test@lender.com",
    "status": "Active",
    "type": "Some Type",
    "sla_days": 7,
}
lender_user = {
    "id": 2,
    "email": "lender-user@example.com",
    "name": "Test lender",
    "type": models.UserType.FI,
    "lender_id": 1,
}

application_payload = {"status": models.ApplicationStatus.PENDING}
application_accepted_payload = {"status": models.ApplicationStatus.ACCEPTED}
application_with_lender_payload = {"status": models.ApplicationStatus.STARTED, "lender_id": 1}

runner = CliRunner()


def test_send_reminders_intro(client, mock_send_templated_email):
    client.post("/create-test-application", json=application_payload)
    client.get("/set-test-application-to-remind/id/1")

    result = runner.invoke(commands.app, ["send-reminders"])

    assert result.exit_code == 0
    assert result.stdout == ""
    assert mock_send_templated_email.call_count == 1


def test_send_reminders_submit(client, mock_send_templated_email):
    client.post("/create-test-application", json=application_accepted_payload)
    client.get("/set-test-application-to-remind-submit/id/1")

    result = runner.invoke(commands.app, ["send-reminders"])

    assert result.exit_code == 0
    assert result.stdout == ""
    assert mock_send_templated_email.call_count == 1


def test_send_reminders_no_applications_to_remind(client, mock_send_templated_email):
    client.post("/create-test-application", json=application_payload)

    result = runner.invoke(commands.app, ["send-reminders"])

    assert result.exit_code == 0
    assert result.stdout == ""
    assert mock_send_templated_email.call_count == 0


def test_set_lapsed_applications(client):
    client.post("/create-test-application", json=application_payload)
    client.get("/set-test-application-as-lapsed/id/1")

    result = runner.invoke(commands.app, ["update-applications-to-lapsed"])

    assert result.exit_code == 0
    assert result.stdout == ""


def test_set_lapsed_applications_no_lapsed(client):
    client.post("/create-test-application", json=application_payload)

    result = runner.invoke(commands.app, ["update-applications-to-lapsed"])

    assert result.exit_code == 0
    assert result.stdout == ""


def test_send_overdue_reminders(client, mock_send_templated_email):
    ocp_headers = client.post("/create-test-user-headers", json=ocp_user).json()
    client.post("/lenders", json=lender, headers=ocp_headers)
    client.post("/create-test-application", json=application_with_lender_payload)

    client.get("/set-application-as-overdue/id/1")
    result = runner.invoke(commands.app, ["sla-overdue-applications"])

    assert result.exit_code == 0
    assert result.stdout == ""
    assert mock_send_templated_email.call_count == 2


def test_send_overdue_reminders_empty(client, mock_send_templated_email):
    ocp_headers = client.post("/create-test-user-headers", json=ocp_user).json()
    client.post("/lenders", json=lender, headers=ocp_headers)
    client.post("/create-test-application", json=application_with_lender_payload)

    client.get("/set-application-as-started/id/1")
    result = runner.invoke(commands.app, ["sla-overdue-applications"])

    assert result.exit_code == 0
    assert result.stdout == ""
    assert mock_send_templated_email.call_count == 0


def test_remove_data(client):
    client.post("/create-test-application", json=application_payload)
    client.get("/set-test-application-as-dated/id/1")

    client.post(
        "/applications/1/update-test-application-status",
        json={"status": models.ApplicationStatus.DECLINED},
    )
    result = runner.invoke(commands.app, ["remove-dated-application-data"])

    assert result.exit_code == 0
    assert result.stdout == ""


def test_remove_data_no_dated_application(client):
    client.post("/create-test-application", json=application_payload)

    result = runner.invoke(commands.app, ["remove-dated-application-data"])

    assert result.exit_code == 0
    assert result.stdout == ""


def test_update_statistic(engine, create_and_drop_database):
    result = runner.invoke(commands.app, ["update-statistics"])

    assert result.exit_code == 0
    assert result.stdout == ""


def test_statistics(client):
    ocp_headers = client.post("/create-test-user-headers", json=ocp_user).json()
    client.post("/lenders", json=lender, headers=ocp_headers)
    lender_headers = client.post("/create-test-user-headers", json=lender_user).json()

    response = client.get("/statistics-ocp", headers=ocp_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/statistics-ocp/opt-in", headers=ocp_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/statistics-fi", headers=lender_headers)
    assert response.status_code == status.HTTP_200_OK
