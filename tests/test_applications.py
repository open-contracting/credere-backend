import os
from unittest.mock import patch

from fastapi import status

from app import models, util

from tests.common.common_test_client import mock_cognito_client  # isort:skip # noqa
from tests.common.common_test_client import mock_templated_email  # isort:skip # noqa
from tests.common.common_test_client import mock_ses_client  # isort:skip # noqa
from tests.common.common_test_client import app, client  # isort:skip # noqa
from tests.common.common_test_client import MockResponse  # isort:skip # noqa

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
file = os.path.join(__location__, "file.jpeg")
wrong_file = os.path.join(__location__, "file.gif")

FI_user = {
    "email": "FI_user@noreply.open-contracting.org",
    "name": "Test FI",
    "type": models.UserType.FI.value,
}


FI_user_with_lender = {
    "id": 2,
    "email": "FI_user_with_lender@noreply.open-contracting.org",
    "name": "Test FI with lender",
    "type": models.UserType.FI.value,
    "lender_id": 1,
}

FI_user_with_lender_2 = {
    "id": 3,
    "email": "FI_user_with_lender_2@noreply.open-contracting.org",
    "name": "Test FI with lender 2",
    "type": models.UserType.FI.value,
    "lender_id": 2,
}

OCP_user = {
    "email": "OCP_user@noreply.open-contracting.org",
    "name": "OCP_user@noreply.open-contracting.org",
    "type": models.UserType.OCP.value,
}

application_base = {"uuid": "123-456-789"}
application_payload = {"status": models.ApplicationStatus.PENDING.value}
application_with_lender_payload = {
    "status": models.ApplicationStatus.PENDING.value,
    "lender_id": 1,
    "credit_product_id": 1,
}
application_with_credit_product = {
    "status": models.ApplicationStatus.ACCEPTED.value,
    "credit_product_id": 1,
}
application_lapsed_payload = {"status": models.ApplicationStatus.LAPSED.value}
application_declined_payload = {"status": models.ApplicationStatus.DECLINED.value}
borrower_declined_oportunity_payload = {"status": models.BorrowerStatus.DECLINE_OPPORTUNITIES.value}
application_credit_option = {
    "uuid": "123-456-789",
    "borrower_size": models.BorrowerSize.SMALL.value,
    "amount_requested": 10000,
}

application_select_credit_option = {
    "uuid": "123-456-789",
    "borrower_size": models.BorrowerSize.SMALL.value,
    "amount_requested": 10000,
    "sector": "adminstration",
    "credit_product_id": 1,
}

lender = {
    "id": 1,
    "name": "test",
    "email_group": "test@noreply.open-contracting.org",
    "status": "Active",
    "type": "Some Type",
    "sla_days": 7,
}

lender_2 = {
    "id": 2,
    "name": "test 2",
    "email_group": "test@noreply.open-contracting.org",
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

update_award = {"title": "new test title"}

update_borrower = {"legal_name": "new_legal_name"}


def test_reject_application(client, mock_templated_email):  # noqa
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    client.post("/lenders", json=lender, headers=OCP_headers)
    FI_headers = client.post("/create-test-user-headers", json=FI_user_with_lender).json()
    client.post("/create-test-credit-option", json=test_credit_option)
    client.post("/create-test-application", json=application_with_lender_payload)

    # tries to reject the application before its started
    response = client.post(
        "/applications/1/reject-application",
        json=reject_payload,
        headers=FI_headers,
    )
    assert response.status_code == status.HTTP_409_CONFLICT

    response = client.post(
        "/applications/1/update-test-application-status",
        json={"status": models.ApplicationStatus.STARTED.value},
    )

    response = client.post(
        "/applications/1/reject-application",
        json=reject_payload,
        headers=FI_headers,
    )
    assert response.json()["status"] == models.ApplicationStatus.REJECTED.value
    assert response.status_code == status.HTTP_200_OK

    response = client.post("/applications/find-alternative-credit-option", json=application_base)
    assert response.status_code == status.HTTP_200_OK


def test_rollback_credit_product(client, mock_templated_email):  # noqa
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    client.post("/lenders", json=lender, headers=OCP_headers)
    client.post("/create-test-credit-option", json=test_credit_option)
    client.post("/create-test-application", json=application_with_credit_product)

    response = client.post(
        "/applications/rollback-select-credit-product",
        json=application_select_credit_option,
    )
    assert response.status_code == status.HTTP_200_OK


def test_access_expired_application(client):  # noqa
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    client.post("/lenders", json=lender, headers=OCP_headers)
    client.post("/create-test-credit-option", json=test_credit_option)
    client.post("/create-test-application", json=application_with_credit_product)

    response = client.get("/set-application-as-expired/id/1")
    # borrower tries to access expired application
    response = client.get("/applications/uuid/123-456-789")
    assert response.status_code == status.HTTP_409_CONFLICT


def test_approve_application_cicle(client, mock_templated_email):  # noqa
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    client.post("/lenders", json=lender, headers=OCP_headers)
    FI_headers = client.post("/create-test-user-headers", json=FI_user_with_lender).json()

    client.post("/lenders", json=lender_2, headers=OCP_headers)
    FI_headers_2 = client.post("/create-test-user-headers", json=FI_user_with_lender_2).json()
    client.post("/create-test-credit-option", json=test_credit_option)
    client.post("/create-test-application", json=application_with_lender_payload)

    # this will mock the previous award get to return an empty array
    with patch(
        "app.sources.colombia.get_previous_contracts",
        return_value=MockResponse(status.HTTP_200_OK, {}),
    ):
        response = client.post("/applications/access-scheme", json=application_base)
        assert response.json()["application"]["status"] == models.ApplicationStatus.ACCEPTED.value
        assert response.status_code == status.HTTP_200_OK

        # Application should be accepted now so it cannot be accepted again
        response = client.post("/applications/access-scheme", json=application_base)
        assert response.status_code == status.HTTP_409_CONFLICT

    response = client.post("/applications/credit-product-options", json=application_credit_option)
    assert response.status_code == status.HTTP_200_OK

    response = client.post("/applications/select-credit-product", json=application_select_credit_option)
    assert response.status_code == status.HTTP_200_OK

    response = client.post("/applications/confirm-credit-product", json=application_base)
    assert response.status_code == status.HTTP_200_OK

    # FI user tries to fecth previous awards
    response = client.get("/applications/1/previous-awards", headers=FI_headers)
    assert response.status_code == status.HTTP_200_OK

    # diffrent FI user tries to fecth previous awards
    response = client.get("/applications/1/previous-awards", headers=FI_headers_2)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # different lender tries to get the application
    response = client.get("/applications/id/1", headers=FI_headers_2)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    new_email = "new_test_email@example.com"
    new_wrong_email = "wrong_email@@noreply!$%&/().open-contracting.org"

    # borrower tries to change their email to a non valid one
    response = client.post(
        "/applications/change-email",
        json={"uuid": "123-456-789", "new_email": new_wrong_email},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    response = client.post(
        "/applications/change-email",
        json={"uuid": "123-456-789", "new_email": new_email},
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.post(
        "/applications/change-email",
        json={"uuid": "123-456-789", "new_email": new_email},
    )
    assert response.status_code == status.HTTP_200_OK

    confirmation_email_token = util.generate_uuid(new_email)

    response = client.post(
        "/applications/confirm-change-email",
        json={
            "uuid": "123-456-789",
            "confirmation_email_token": confirmation_email_token,
        },
    )
    assert response.status_code == status.HTTP_200_OK

    # borrower tries to confirm email without a pending change
    response = client.post(
        "/applications/confirm-change-email",
        json={
            "uuid": "123-456-789",
            "confirmation_email_token": "confirmation_email_token",
        },
    )
    assert response.status_code == status.HTTP_409_CONFLICT

    response = client.post("/applications/submit", json=application_base)
    assert response.json()["application"]["status"] == models.ApplicationStatus.SUBMITTED.value
    assert response.status_code == status.HTTP_200_OK

    # tries to upload document before application starting
    with open(file, "rb") as file_to_upload:
        response = client.post(
            "/applications/upload-document",
            data={
                "uuid": "123-456-789",
                "type": models.BorrowerDocumentType.INCORPORATION_DOCUMENT.value,
            },
            files={"file": (file_to_upload.name, file_to_upload, "image/jpeg")},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # different FI user tries to start the application
    response = client.post("/applications/1/start", headers=FI_headers_2)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # different FI user tries to update the award
    response = client.put("/applications/1/award", json=update_award, headers=FI_headers_2)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # different FI user tries to update the borrower
    response = client.put("/applications/1/award", json=update_borrower, headers=FI_headers_2)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Fi user starts application
    response = client.post("/applications/1/start", headers=FI_headers)
    assert response.json()["status"] == models.ApplicationStatus.STARTED.value
    assert response.status_code == status.HTTP_200_OK

    # different FI user tries to update the award
    response = client.put(
        "/applications/1/award",
        json=update_award,
        headers=FI_headers_2,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN

    # different FI user tries to update the borrower
    response = client.put(
        "/applications/1/borrower",
        json=update_borrower,
        headers=FI_headers_2,
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # FI user tries to update non existing award
    response = client.put(
        "/applications/100/award",
        json=update_award,
        headers=FI_headers,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # FI user tries to update non existing borrower
    response = client.put(
        "/applications/100/borrower",
        json=update_borrower,
        headers=FI_headers,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # FI user tries to update the award
    response = client.put(
        "/applications/1/award",
        json=update_award,
        headers=FI_headers,
    )
    assert response.json()["award"]["title"] == update_award["title"]
    assert response.status_code == status.HTTP_200_OK

    # FI user tries to update the borrower
    response = client.put(
        "/applications/1/borrower",
        json=update_borrower,
        headers=FI_headers,
    )
    assert response.json()["borrower"]["legal_name"] == update_borrower["legal_name"]
    assert response.status_code == status.HTTP_200_OK

    response = client.post(
        "applications/email-sme/1",
        json={"message": "test message"},
        headers=FI_headers,
    )

    assert response.json()["status"] == models.ApplicationStatus.INFORMATION_REQUESTED.value
    assert response.status_code == status.HTTP_200_OK

    # borrower uploads the wrong type of document
    with open(wrong_file, "rb") as file_to_upload:
        response = client.post(
            "/applications/upload-document",
            data={
                "uuid": "123-456-789",
                "type": models.BorrowerDocumentType.INCORPORATION_DOCUMENT.value,
            },
            files={"file": (file_to_upload.name, file_to_upload, "image/jpeg")},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    with open(file, "rb") as file_to_upload:
        response = client.post(
            "/applications/upload-document",
            data={
                "uuid": "123-456-789",
                "type": models.BorrowerDocumentType.INCORPORATION_DOCUMENT.value,
            },
            files={"file": (file_to_upload.name, file_to_upload, "image/jpeg")},
        )
        assert response.status_code == status.HTTP_200_OK

        response = client.get("/applications/documents/id/1", headers=FI_headers)
        assert response.status_code == status.HTTP_200_OK

        # OCP user downloads the document
        response = client.get("/applications/documents/id/1", headers=OCP_headers)
        assert response.status_code == status.HTTP_200_OK

        # OCP ask for a file that does not exist
        response = client.get("/applications/documents/id/100", headers=OCP_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        response = client.post("/applications/complete-information-request", json={"uuid": "123-456-789"})
        assert response.json()["application"]["status"] == models.ApplicationStatus.STARTED.value
        assert response.status_code == status.HTTP_200_OK

    # lender tries to approve the application without verifing legal_name
    response = client.post(
        "/applications/1/approve-application",
        json=approve_application,
        headers=FI_headers,
    )
    assert response.status_code == status.HTTP_409_CONFLICT

    # verifly legal_name
    response = client.put(
        "/applications/1/verify-data-field",
        json={"legal_name": True},
        headers=FI_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    # lender tries to approve the application without verifing INCORPORATION_DOCUMENT
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

    # lender approves application
    response = client.post(
        "/applications/1/approve-application",
        json=approve_application,
        headers=FI_headers,
    )
    assert response.json()["status"] == models.ApplicationStatus.APPROVED.value
    assert response.status_code == status.HTTP_200_OK

    # msme uploads contract
    with open(file, "rb") as file_to_upload:
        response = client.post(
            "/applications/upload-contract",
            data={"uuid": "123-456-789"},
            files={"file": (file_to_upload.name, file_to_upload, "image/jpeg")},
        )
        assert response.status_code == status.HTTP_200_OK

    response = client.post(
        "/applications/confirm-upload-contract",
        json={"uuid": "123-456-789", "contract_amount_submitted": 100000},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["application"]["status"] == models.ApplicationStatus.CONTRACT_UPLOADED.value

    response = client.post(
        "/applications/1/complete-application",
        json={"disbursed_final_amount": 10000},
        headers=FI_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == models.ApplicationStatus.COMPLETED.value


def test_get_applications(client):  # noqa
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    client.post("/lenders", json=lender, headers=OCP_headers)
    FI_headers = client.post("/create-test-user-headers", json=FI_user_with_lender).json()

    client.post("/create-test-credit-option", json=test_credit_option)
    client.post("/create-test-application", json=application_with_lender_payload)

    response = client.get(
        "/applications/admin-list/?page=1&page_size=4&sort_field=borrower.legal_name&sort_order=asc",
        headers=OCP_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/applications/admin-list/?page=1&page_size=4&sort_field=borrower.legal_name&sort_order=asc")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    response = client.get("/applications/id/1", headers=OCP_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/applications/id/1", headers=FI_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/applications/id/1")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # tries to get a non existing application
    response = client.get("/applications/id/100", headers=FI_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND

    response = client.get("/applications", headers=FI_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/applications")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    response = client.get("/applications/uuid/123-456-789")
    assert response.status_code == status.HTTP_200_OK

    client.post("/change-test-application-status", json=application_lapsed_payload)
    response = client.get("/applications/uuid/123-456-789")
    assert response.status_code == status.HTTP_409_CONFLICT

    response = client.get("/applications/uuid/123-456")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    response = client.post("/applications/access-scheme", json={"uuid": "123-456"})
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_application_declined(client, mock_templated_email):  # noqa
    client.post("/create-test-application", json=application_payload)

    response = client.post(
        "/applications/decline",
        json={"uuid": "123-456-789", "decline_this": False, "decline_all": True},
    )
    assert response.json()["application"]["status"] == models.ApplicationStatus.DECLINED.value
    assert response.json()["borrower"]["status"] == models.BorrowerStatus.DECLINE_OPPORTUNITIES.value
    assert response.status_code == status.HTTP_200_OK

    response = client.post("/applications/access-scheme", json={"uuid": "123-456-789"})
    assert response.status_code == status.HTTP_409_CONFLICT


def test_application_rollback_declined(client):  # isort:skip # noqa
    client.post("/create-test-application", json=application_declined_payload)
    client.post("/change-test-borrower-status", json=borrower_declined_oportunity_payload)

    response = client.post("/applications/rollback-decline", json={"uuid": "123-456-789"})

    assert response.json()["application"]["status"] == models.ApplicationStatus.PENDING.value
    assert response.json()["borrower"]["status"] == models.BorrowerStatus.ACTIVE.value
    assert response.status_code == status.HTTP_200_OK

    response = client.post("/applications/rollback-decline", json={"uuid": "123-456-789"})
    assert response.status_code == status.HTTP_409_CONFLICT


def test_application_declined_feedback(client):  # isort:skip # noqa
    client.post(
        "/create-test-application",
        json={"status": models.ApplicationStatus.DECLINED.value},
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
    assert response.json()["application"]["status"] == models.ApplicationStatus.DECLINED.value
    assert response.status_code == status.HTTP_200_OK
