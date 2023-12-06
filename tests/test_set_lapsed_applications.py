from app import models
from app.commands import update_applications_to_lapsed

application_payload = {"status": models.ApplicationStatus.PENDING}


def test_set_lapsed_applications(client):
    client.post("/create-test-application", json=application_payload)
    client.get("/set-test-application-as-lapsed/id/1")
    update_applications_to_lapsed()


def test_set_lapsed_applications_no_lapsed(client):
    client.post("/create-test-application", json=application_payload)
    update_applications_to_lapsed()
