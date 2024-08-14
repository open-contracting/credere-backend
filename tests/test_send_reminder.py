from app import models
from app.commands import send_reminders

application_payload = {"status": models.ApplicationStatus.PENDING}
application_accepted_payload = {"status": models.ApplicationStatus.ACCEPTED}


def test_send_reminders_intro(client, mock_send_templated_email):
    client.post("/create-test-application", json=application_payload)
    client.get("/set-test-application-to-remind/id/1")
    send_reminders()
    assert mock_send_templated_email.call_count == 1


def test_send_reminders_submit(client, mock_send_templated_email):
    client.post("/create-test-application", json=application_accepted_payload)
    client.get("/set-test-application-to-remind/id/1")
    send_reminders()
    assert mock_send_templated_email.call_count == 1


def test_send_reminders_no_applications_to_remind(client, mock_send_templated_email):
    client.post("/create-test-application", json=application_payload)
    send_reminders()
    assert mock_send_templated_email.call_count == 0
