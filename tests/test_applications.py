import logging
import os
from unittest.mock import patch

from fastapi import status

from app.schema import core

from tests.common.common_test_client import mock_cognito_client  # isort:skip # noqa
from tests.common.common_test_client import mock_ses_client  # isort:skip # noqa
from tests.common.common_test_client import app, client  # isort:skip # noqa
from tests.common.common_test_client import MockResponse  # isort:skip # noqa

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
file = os.path.join(__location__, "file.jpeg")

FI_user = {
    "email": "FI_user@example.com",
    "name": "Test FI",
    "type": core.UserType.FI.value,
}


FI_user_with_lender = {
    "id": 2,
    "email": "FI_user_with_lender@example.com",
    "name": "Test FI with lender",
    "type": core.UserType.FI.value,
    "lender_id": 1,
}

FI_user_with_lender_2 = {
    "id": 3,
    "email": "FI_user_with_lender_2@example.com",
    "name": "Test FI with lender 2",
    "type": core.UserType.FI.value,
    "lender_id": 2,
}

OCP_user = {
    "email": "OCP_user@example.com",
    "name": "OCP_user@example.com",
    "type": core.UserType.OCP.value,
}

application_payload = {"status": core.ApplicationStatus.PENDING.value}
application_with_lender_payload = {
    "status": core.ApplicationStatus.PENDING.value,
    "lender_id": 1,
    "credit_product_id": 1,
}
application_lapsed_payload = {"status": core.ApplicationStatus.LAPSED.value}
application_declined_payload = {"status": core.ApplicationStatus.DECLINED.value}
borrower_declined_oportunity_payload = {
    "status": core.BorrowerStatus.DECLINE_OPPORTUNITIES.value
}
lender = {
    "id": 1,
    "name": "test",
    "email_group": "test@lender.com",
    "status": "Active",
    "type": "Some Type",
    "sla_days": 7,
}

lender_2 = {
    "id": 2,
    "name": "test 2",
    "email_group": "test@lender2.com",
    "status": "Active",
    "type": "Some Type",
    "sla_days": 7,
}
reject_payload = {
    "compliance_checks_failed": True,
    "poor_credit_history": True,
    "risk_of_fraud": False,
    "other": True,
    "other_reason": "test rejection message",
}

test_credit_option = {
    "borrower_size": "SMALL",
    "lower_limit": 5000.00,
    "upper_limit": 500000.00,
    "interest_rate": 3.75,
    "type": "LOAN",
    "required_document_types": {
        "INCORPORATION_DOCUMENT": True,
    },
    "other_fees_total_amount": 1000,
    "other_fees_description": "Other test fees",
    "more_info_url": "www.moreinfo.test",
    "lender_id": 1,
}
approve_application = {
    "compliant_checks_completed": True,
    "compliant_checks_passed": True,
    "additional_comments": "test comments",
}


def test_reject_application(client):  # noqa
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    client.post("/lenders", json=lender, headers=OCP_headers)
    FI_headers = client.post(
        "/create-test-user-headers", json=FI_user_with_lender
    ).json()
    client.post("/create-test-credit-option", json=test_credit_option)
    client.post("/create-test-application", json=application_with_lender_payload)

    response = client.post(
        "/applications/1/update-test-application-status",
        json={"status": core.ApplicationStatus.STARTED.value},
    )

    with patch(
        "app.utils.email_utility.send_rejected_application_email_without_alternatives",
        return_value=123456,
    ):
        response = client.post(
            "/applications/1/reject-application",
            json=reject_payload,
            headers=FI_headers,
        )
        assert response.json()["status"] == core.ApplicationStatus.REJECTED.value
        assert response.status_code == status.HTTP_200_OK


def test_approve_application_cicle(client, mocker):  # noqa
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    client.post("/lenders", json=lender, headers=OCP_headers)
    FI_headers = client.post(
        "/create-test-user-headers", json=FI_user_with_lender
    ).json()
    client.post("/create-test-credit-option", json=test_credit_option)
    client.post("/create-test-application", json=application_with_lender_payload)

    # this will mock the previous award get to return an empty array
    with patch(
        "app.background_processes.awards_utils.get_previous_contracts",
        return_value=MockResponse(status.HTTP_200_OK, {}),
    ):
        response = client.post(
            "/applications/access-scheme", json={"uuid": "123-456-789"}
        )

        assert (
            response.json()["application"]["status"]
            == core.ApplicationStatus.ACCEPTED.value
        )
        assert response.status_code == status.HTTP_200_OK

        logging.info(
            "Application should be accepted now so it cannot be accepted again"
        )
        response = client.post(
            "/applications/access-scheme", json={"uuid": "123-456-789"}
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    with patch(
        "app.utils.email_utility.send_new_email_confirmation",
        return_value="123456",
    ), patch(
        "app.utils.applications.check_pending_email_confirmation",
        return_value=None,
    ):
        response = client.post(
            "/applications/change-email",
            json={"uuid": "123-456-789", "new_email": "new_test_email@example.com"},
        )
        assert response.status_code == status.HTTP_200_OK

        response = client.post(
            "/applications/confirm-change-email",
            json={
                "uuid": "123-456-789",
                "confirmation_email_token": "test-token",
            },
        )
        assert response.status_code == status.HTTP_200_OK

    with patch(
        "app.utils.email_utility.send_notification_new_app_to_fi",
        return_value="123456",
    ), patch(
        "app.utils.email_utility.send_notification_new_app_to_ocp",
        return_value="456789",
    ):
        response = client.post("/applications/submit", json={"uuid": "123-456-789"})
        assert (
            response.json()["application"]["status"]
            == core.ApplicationStatus.SUBMITTED.value
        )

        assert response.status_code == status.HTTP_200_OK

    # tries to upload document before application starting
    with open(file, "rb") as file_to_upload:
        response = client.post(
            "/applications/upload-document",
            data={
                "uuid": "123-456-789",
                "type": core.BorrowerDocumentType.INCORPORATION_DOCUMENT.value,
            },
            files={"file": (file_to_upload.name, file_to_upload, "image/jpeg")},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # lender starts application
    response = client.post("/applications/1/start", headers=FI_headers)
    assert response.json()["status"] == core.ApplicationStatus.STARTED.value
    assert response.status_code == status.HTTP_200_OK

    with patch(
        "app.utils.email_utility.send_mail_request_to_sme",
        return_value="123456",
    ):
        response = client.post(
            "applications/email-sme/1",
            json={"message": "test message"},
            headers=FI_headers,
        )

        assert (
            response.json()["status"]
            == core.ApplicationStatus.INFORMATION_REQUESTED.value
        )
        assert response.status_code == status.HTTP_200_OK

    with patch(
        "app.utils.email_utility.send_upload_documents_notifications_to_FI",
        return_value="123456",
    ), open(file, "rb") as file_to_upload:
        response = client.post(
            "/applications/upload-document",
            data={
                "uuid": "123-456-789",
                "type": core.BorrowerDocumentType.INCORPORATION_DOCUMENT.value,
            },
            files={"file": (file_to_upload.name, file_to_upload, "image/jpeg")},
        )
        assert response.status_code == status.HTTP_200_OK

        response = client.post(
            "/applications/1/upload-compliance",
            files={"file": (file_to_upload.name, file_to_upload, "image/jpeg")},
            headers=FI_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        response = client.get("/applications/documents/id/1", headers=FI_headers)
        assert response.status_code == status.HTTP_200_OK

        response = client.post(
            "/applications/complete-information-request", json={"uuid": "123-456-789"}
        )
        assert (
            response.json()["application"]["status"]
            == core.ApplicationStatus.STARTED.value
        )
        assert response.status_code == status.HTTP_200_OK

    # lender tries to approve the application without verifing legal_name
    response = client.post(
        "/applications/1/approve-application",
        json=approve_application,
        headers=FI_headers,
    )
    assert response.status_code == status.HTTP_409_CONFLICT

    # verifly borrower document
    response = client.put(
        "/applications/documents/1/verify-document",
        json={"verified": True},
        headers=FI_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    # verifly legal_name
    response = client.put(
        "/applications/1/verify-data-field",
        json={"legal_name": True},
        headers=FI_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    # lender approves application
    with patch(
        "app.utils.email_utility.send_application_approved_email", return_value="123456"
    ):
        response = client.post(
            "/applications/1/approve-application",
            json=approve_application,
            headers=FI_headers,
        )
        assert response.json()["status"] == core.ApplicationStatus.APPROVED.value
        assert response.status_code == status.HTTP_200_OK

    # msme uploads contract
    with open(file, "rb") as file_to_upload:
        response = client.post(
            "/applications/upload-contract",
            data={"uuid": "123-456-789"},
            files={"file": (file_to_upload.name, file_to_upload, "image/jpeg")},
        )
        assert response.status_code == status.HTTP_200_OK

    with patch(
        "app.utils.email_utility.send_upload_contract_notification_to_FI",
        return_value="123456",
    ), patch(
        "app.utils.email_utility.send_upload_contract_confirmation",
        return_value="123456",
    ):
        response = client.post(
            "/applications/confirm-upload-contract",
            json={"uuid": "123-456-789", "contract_amount_submitted": 100000},
        )
        assert response.status_code == status.HTTP_200_OK
        assert (
            response.json()["application"]["status"]
            == core.ApplicationStatus.CONTRACT_UPLOADED.value
        )

    response = client.post(
        "/applications/1/complete-application",
        json={"disbursed_final_amount": 10000},
        headers=FI_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == core.ApplicationStatus.COMPLETED.value


def test_get_applications(client):  # noqa
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    client.post("/lenders", json=lender, headers=OCP_headers)
    FI_headers = client.post(
        "/create-test-user-headers", json=FI_user_with_lender
    ).json()

    client.post("/create-test-credit-option", json=test_credit_option)
    client.post("/create-test-application", json=application_with_lender_payload)

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
    client.post("/change-test-application-status", json=application_lapsed_payload)
    response = client.get("/applications/uuid/123-456-789")
    assert response.status_code == status.HTTP_409_CONFLICT

    response = client.get("/applications/uuid/123-456")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    logging.info("Search for a non existent application")
    response = client.post("/applications/access-scheme", json={"uuid": "123-456"})
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_application_declined(client):  # noqa
    client.post("/create-test-application", json=application_payload)

    response = client.post(
        "/applications/decline",
        json={"uuid": "123-456-789", "decline_this": False, "decline_all": True},
    )
    assert (
        response.json()["application"]["status"]
        == core.ApplicationStatus.DECLINED.value
    )
    assert (
        response.json()["borrower"]["status"]
        == core.BorrowerStatus.DECLINE_OPPORTUNITIES.value
    )
    assert response.status_code == status.HTTP_200_OK

    logging.info("Application should be accepted now because it was declined")
    response = client.post("/applications/access-scheme", json={"uuid": "123-456-789"})
    assert response.status_code == status.HTTP_409_CONFLICT


def test_application_rollback_declined(client):  # isort:skip # noqa
    client.post("/create-test-application", json=application_declined_payload)
    client.post(
        "/change-test-borrower-status", json=borrower_declined_oportunity_payload
    )

    response = client.post(
        "/applications/rollback-decline", json={"uuid": "123-456-789"}
    )

    assert (
        response.json()["application"]["status"] == core.ApplicationStatus.PENDING.value
    )
    assert response.json()["borrower"]["status"] == core.BorrowerStatus.ACTIVE.value
    assert response.status_code == status.HTTP_200_OK

    logging.info("Application is not rejected now so it cannot be rolled back again")
    response = client.post(
        "/applications/rollback-decline", json={"uuid": "123-456-789"}
    )
    assert response.status_code == status.HTTP_409_CONFLICT


def test_application_declined_feedback(client):  # isort:skip # noqa
    client.post(
        "/create-test-application",
        json={"status": core.ApplicationStatus.DECLINED.value},
    )

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
    assert (
        response.json()["application"]["status"]
        == core.ApplicationStatus.DECLINED.value
    )
    assert response.status_code == status.HTTP_200_OK
