import logging

from fastapi import status

import tests.test_client as test_client
from app.schema.core import ApplicationStatus, BorrowerStatus

from tests.test_client import app, client  # isort:skip # noqa
from tests.test_client import mock_cognito_client, mock_ses_client  # isort:skip # noqa


def test_get_applications(client):  # isort:skip # noqa
    logging.info("Pre load users for this test")
    OCP_headers = test_client.create_test_user(client, test_client.OCP_user)
    FI_headers = test_client.create_test_user(client, test_client.FI_user)
    logging.info(
        "Pre load an application with its related award and borrower for this test"
    )
    test_client.create_application()

    logging.info("Test different get methods and permissions for getting applications")
    response = client.get(
        "/applications/admin-list/?page=1&page_size=4&sort_field=borrower.legal_name&sort_order=asc",
        headers=OCP_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.get(
        "/applications/admin-list/?page=1&page_size=4&sort_field=borrower.legal_name&sort_order=asc"
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    response = client.get("/applications/id/1", headers=OCP_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/applications/id/1")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    logging.info("get only applications related to FI user")
    response = client.get("/applications", headers=FI_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/applications")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    response = client.get("/applications/uuid/123-456-789")
    assert response.status_code == status.HTTP_200_OK

    logging.info("set application to expire so use cannot get it")
    test_client.set_application_as_expired()
    response = client.get("/applications/uuid/123-456-789")
    assert response.status_code == status.HTTP_409_CONFLICT

    response = client.get("/applications/uuid/123-456")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    logging.info("Search for a non existent application")
    response = client.post("/applications/access-scheme", json={"uuid": "123-456"})
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_application_declined(client):  # isort:skip # noqa
    test_client.create_application()

    response = client.post(
        "/applications/decline",
        json={"uuid": "123-456-789", "decline_this": False, "decline_all": True},
    )
    assert response.json()["application"]["status"] == ApplicationStatus.DECLINED.value
    assert (
        response.json()["borrower"]["status"]
        == BorrowerStatus.DECLINE_OPPORTUNITIES.value
    )
    assert response.status_code == status.HTTP_200_OK

    logging.info("Application should be accepted now because it was declined")
    response = client.post("/applications/access-scheme", json={"uuid": "123-456-789"})
    assert response.status_code == status.HTTP_409_CONFLICT


def test_application_rollback_declined(client):  # isort:skip # noqa
    test_client.create_application(ApplicationStatus.DECLINED)
    test_client.set_borrower_status(BorrowerStatus.DECLINE_OPPORTUNITIES)

    response = client.post(
        "/applications/rollback-decline", json={"uuid": "123-456-789"}
    )

    assert response.json()["application"]["status"] == ApplicationStatus.PENDING.value
    assert response.json()["borrower"]["status"] == BorrowerStatus.ACTIVE.value
    assert response.status_code == status.HTTP_200_OK

    logging.info("Application is not rejected now so it cannot be rolled back again")
    response = client.post(
        "/applications/rollback-decline", json={"uuid": "123-456-789"}
    )
    assert response.status_code == status.HTTP_409_CONFLICT


def test_application_declined_feedback(client):  # isort:skip # noqa
    test_client.create_application(ApplicationStatus.DECLINED)

    declined_feedback = {
        "uuid": "123-456-789",
        "dont_need_access_credit": True,
        "already_have_acredit": False,
        "preffer_to_go_to_bank": False,
        "dont_want_access_credit": False,
        "other": False,
        "other_comments": "comments",
    }

    response = client.post("/applications/decline-feedback", json=declined_feedback)
    assert response.json()["application"]["status"] == ApplicationStatus.DECLINED.value
    assert response.status_code == status.HTTP_200_OK


def test_access_scheme(client):  # isort:skip # noqa
    test_client.create_application(ApplicationStatus.PENDING)

    response = client.post("/applications/access-scheme", json={"uuid": "123-456-789"})
    assert response.json()["application"]["status"] == ApplicationStatus.ACCEPTED.value
    assert response.status_code == status.HTTP_200_OK

    logging.info("Application should be accepted now so it cannot be accepted again")
    response = client.post("/applications/access-scheme", json={"uuid": "123-456-789"})
    assert response.status_code == status.HTTP_409_CONFLICT
