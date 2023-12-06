from app import models
from app.commands import remove_dated_application_data

application_payload = {"status": models.ApplicationStatus.PENDING}


def test_remove_data(client):
    client.post("/create-test-application", json=application_payload)
    client.get("/set-test-application-as-dated/id/1")
    client.post(
        "/applications/1/update-test-application-status",
        json={"status": models.ApplicationStatus.DECLINED},
    )

    remove_dated_application_data()


def test_remove_data_no_dated_application(client):
    client.post("/create-test-application", json=application_payload)

    remove_dated_application_data()
