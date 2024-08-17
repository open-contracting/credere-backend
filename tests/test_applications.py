import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi import status

from app import models, util
from app.db import engine
from tests import MockResponse, assert_ok, get_test_db
from tests.test_fetcher import _load_json_file

BASEDIR = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


def test_reject_application(client, session, lender_header, pending_application, application_uuid_payload):
    appid = pending_application.id
    payload = {
        "compliance_checks_failed": True,
        "poor_credit_history": True,
        "risk_of_fraud": False,
        "other": True,
        "other_reason": "test rejection message",
    }

    # tries to reject the application before its started
    response = client.post(f"/applications/{appid}/reject-application", json=payload, headers=lender_header)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "Application status should not be PENDING"}

    pending_application.status = models.ApplicationStatus.STARTED
    session.commit()

    response = client.post(f"/applications/{appid}/reject-application", json=payload, headers=lender_header)
    assert_ok(response)
    assert response.json()["status"] == models.ApplicationStatus.REJECTED

    response = client.post("/applications/find-alternative-credit-option", json=application_uuid_payload)
    assert_ok(response)


def test_rollback_credit_product(client, accepted_application):
    response = client.post(
        "/applications/rollback-select-credit-product",
        json={
            "uuid": "123-456-789",
            "borrower_size": models.BorrowerSize.SMALL,
            "amount_requested": 10000,
            "sector": "adminstration",
            "credit_product_id": accepted_application.credit_product_id,
        },
    )

    assert_ok(response)
    assert response.json()["application"]["uuid"] == "123-456-789"
    assert response.json()["application"]["credit_product_id"] is None
    assert response.json()["application"]["borrower_credit_product_selected_at"] is None


def test_access_expired_application(client, session, pending_application):
    pending_application.expired_at = datetime.now(pending_application.created_at.tzinfo) - timedelta(days=+1)
    session.commit()

    # borrower tries to access expired application
    response = client.get("/applications/uuid/123-456-789")

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "Application expired"}


def test_approve_application_cycle(
    client,
    session,
    admin_header,
    lender_header,
    unauthorized_lender_header,
    pending_application,
    application_uuid_payload,
):
    appid = pending_application.id
    source_award = _load_json_file("fixtures/award.json")
    new_email = "newtestemail@gmail.com"
    file = os.path.join(BASEDIR, "fixtures", "file.jpeg")
    award_payload = {"title": "new test title"}
    borrower_payload = {"legal_name": "new_legal_name"}
    approve_payload = {
        "compliant_checks_completed": True,
        "compliant_checks_passed": True,
        "additional_comments": "test comments",
    }

    # this will mock the previous award get to return an empty array
    with patch(
        "app.sources.colombia.get_previous_awards",
        return_value=MockResponse(status.HTTP_200_OK, source_award),
    ), patch(
        "app.sources.colombia._get_remote_contract",
        return_value=(_load_json_file("fixtures/contract.json"), "url"),
    ):
        response = client.post("/applications/access-scheme", json=application_uuid_payload)
        assert_ok(response)
        assert response.json()["application"]["status"] == models.ApplicationStatus.ACCEPTED

        # Application should be accepted now so it cannot be accepted again
        response = client.post("/applications/access-scheme", json=application_uuid_payload)
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json() == {"detail": "Application status should not be ACCEPTED"}

    response = client.post(
        "/applications/credit-product-options",
        json={
            "uuid": "123-456-789",
            "borrower_size": models.BorrowerSize.SMALL,
            "amount_requested": 10000,
        },
    )
    assert_ok(response)

    response = client.post(
        "/applications/select-credit-product",
        json={
            "uuid": "123-456-789",
            "borrower_size": models.BorrowerSize.SMALL,
            "amount_requested": 10000,
            "sector": "adminstration",
            "credit_product_id": pending_application.credit_product_id,
        },
    )
    assert_ok(response)

    response = client.post("/applications/confirm-credit-product", json=application_uuid_payload)
    assert_ok(response)

    # Lender user tries to fetch previous awards
    response = client.get(f"/applications/{appid}/previous-awards", headers=lender_header)
    assert_ok(response)
    assert len(response.json()) == len(source_award)
    assert response.json()[0]["previous"] is True
    assert response.json()[0]["entity_code"] == source_award[0]["nit_entidad"]

    # different lender user tries to fetch previous awards
    response = client.get(f"/applications/{appid}/previous-awards", headers=unauthorized_lender_header)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "User is not authorized"}

    # different lender tries to get the application
    response = client.get(f"/applications/id/{appid}", headers=unauthorized_lender_header)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "User is not authorized"}

    # borrower tries to change their email to a non valid one
    response = client.post(
        "/applications/change-email",
        json={"uuid": "123-456-789", "new_email": "wrong_email@@noreply!$%&/().open-contracting.org"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json() == {"detail": "New email is not valid"}

    response = client.post("/applications/change-email", json={"uuid": "123-456-789", "new_email": new_email})
    assert_ok(response)

    response = client.post("/applications/change-email", json={"uuid": "123-456-789", "new_email": new_email})
    assert_ok(response)

    confirmation_email_token = util.generate_uuid(new_email)

    response = client.post(
        "/applications/confirm-change-email",
        json={"uuid": "123-456-789", "confirmation_email_token": confirmation_email_token},
    )
    assert_ok(response)

    # borrower tries to confirm email without a pending change
    response = client.post(
        "/applications/confirm-change-email",
        json={"uuid": "123-456-789", "confirmation_email_token": "confirmation_email_token"},
    )
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "Application is not pending an email confirmation"}

    response = client.post("/applications/submit", json=application_uuid_payload)
    assert_ok(response)
    assert response.json()["application"]["status"] == models.ApplicationStatus.SUBMITTED

    # tries to upload document before application starting
    with open(file, "rb") as file_to_upload:
        response = client.post(
            "/applications/upload-document",
            data={"uuid": "123-456-789", "type": models.BorrowerDocumentType.INCORPORATION_DOCUMENT},
            files={"file": (file_to_upload.name, file_to_upload, "image/jpeg")},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": "Cannot upload document at this stage"}

    # different lender user tries to start the application
    response = client.post(f"/applications/{appid}/start", headers=unauthorized_lender_header)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "User is not authorized"}

    # different lender user tries to update the award
    response = client.put(f"/applications/{appid}/award", json=award_payload, headers=unauthorized_lender_header)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "User is not authorized"}

    # different lender user tries to update the borrower
    response = client.put(f"/applications/{appid}/borrower", json=borrower_payload, headers=unauthorized_lender_header)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "User is not authorized"}

    # The lender user starts application
    response = client.post(f"/applications/{appid}/start", headers=lender_header)
    assert_ok(response)
    assert response.json()["status"] == models.ApplicationStatus.STARTED

    # different lender user tries to update the award
    response = client.put(f"/applications/{appid}/award", json=award_payload, headers=unauthorized_lender_header)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "User is not authorized"}

    # different lender user tries to update the borrower
    response = client.put(f"/applications/{appid}/borrower", json=borrower_payload, headers=unauthorized_lender_header)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "User is not authorized"}

    # Lender user tries to update non existing award
    response = client.put("/applications/999/award", json=award_payload, headers=lender_header)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Application not found"}

    # Lender user tries to update non existing borrower
    response = client.put("/applications/999/borrower", json=borrower_payload, headers=lender_header)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Application not found"}

    # Lender user tries to update the award
    response = client.put(f"/applications/{appid}/award", json=award_payload, headers=lender_header)
    assert_ok(response)
    assert response.json()["award"]["title"] == award_payload["title"]

    # Lender user tries to update the borrower
    response = client.put(f"/applications/{appid}/borrower", json=borrower_payload, headers=lender_header)
    assert_ok(response)
    assert response.json()["borrower"]["legal_name"] == borrower_payload["legal_name"]

    response = client.post(f"applications/email-sme/{appid}", json={"message": "test message"}, headers=lender_header)
    assert_ok(response)
    assert response.json()["status"] == models.ApplicationStatus.INFORMATION_REQUESTED

    # borrower uploads the wrong type of document
    with open(os.path.join(BASEDIR, "fixtures", "file.gif"), "rb") as file_to_upload:
        response = client.post(
            "/applications/upload-document",
            data={"uuid": "123-456-789", "type": models.BorrowerDocumentType.INCORPORATION_DOCUMENT},
            files={"file": (file_to_upload.name, file_to_upload, "image/jpeg")},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.json() == {"detail": "Format not allowed. It must be a PNG, JPEG, or PDF file"}

    with open(file, "rb") as file_to_upload:
        response = client.post(
            "/applications/upload-document",
            data={"uuid": "123-456-789", "type": models.BorrowerDocumentType.INCORPORATION_DOCUMENT},
            files={"file": (file_to_upload.name, file_to_upload, "image/jpeg")},
        )
        assert_ok(response)

        response = client.post("/applications/complete-information-request", json={"uuid": "123-456-789"})
        assert_ok(response)
        assert response.json()["application"]["status"] == models.ApplicationStatus.STARTED

        response = client.get(f"/applications/documents/id/{appid}", headers=lender_header)
        assert_ok(response)

        # OCP user downloads the document
        response = client.get(f"/applications/documents/id/{appid}", headers=admin_header)
        assert_ok(response)

        # OCP ask for a file that does not exist
        response = client.get("/applications/documents/id/999", headers=admin_header)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "BorrowerDocument not found"}

    # lender tries to approve the application without verifying legal_name
    response = client.post(f"/applications/{appid}/approve-application", json=approve_payload, headers=lender_header)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "BORROWER_FIELD_VERIFICATION_MISSING"}

    # verify legal_name
    response = client.put(f"/applications/{appid}/verify-data-field", json={"legal_name": True}, headers=lender_header)
    assert_ok(response)
    assert response.json()["secop_data_verification"] == {
        "legal_name": True,
        "address": True,
        "email": True,
        "legal_identifier": True,
        "sector": True,
        "size": True,
        "type": True,
    }

    # lender tries to approve the application without verifying INCORPORATION_DOCUMENT
    response = client.post(f"/applications/{appid}/approve-application", json=approve_payload, headers=lender_header)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "DOCUMENT_VERIFICATION_MISSING"}

    # verify borrower document
    response = client.put(
        f"/applications/documents/{appid}/verify-document", json={"verified": True}, headers=lender_header
    )
    assert_ok(response)
    assert response.json()["id"] == 1
    with contextmanager(get_test_db(engine))() as session:
        assert session.query(models.BorrowerDocument).one().verified is True

    # lender approves application
    response = client.post(f"/applications/{appid}/approve-application", json=approve_payload, headers=lender_header)
    assert_ok(response)
    assert response.json()["status"] == models.ApplicationStatus.APPROVED

    # Borrower uploads contract
    with open(file, "rb") as file_to_upload:
        response = client.post(
            "/applications/upload-contract",
            data={"uuid": "123-456-789"},
            files={"file": (file_to_upload.name, file_to_upload, "image/jpeg")},
        )
        assert_ok(response)

    response = client.post(
        "/applications/confirm-upload-contract",
        json={"uuid": "123-456-789", "contract_amount_submitted": 100000},
    )
    assert_ok(response)
    assert response.json()["application"]["status"] == models.ApplicationStatus.CONTRACT_UPLOADED

    response = client.post(
        f"/applications/{appid}/complete-application", json={"disbursed_final_amount": 10000}, headers=lender_header
    )
    assert_ok(response)
    assert response.json()["status"] == models.ApplicationStatus.COMPLETED


def test_get_applications(client, session, admin_header, lender_header, pending_application):
    appid = pending_application.id

    response = client.get(
        "/applications/admin-list/?page=1&page_size=4&sort_field=borrower.legal_name&sort_order=asc",
        headers=admin_header,
    )
    assert_ok(response)

    response = client.get("/applications/admin-list/?page=1&page_size=4&sort_field=borrower.legal_name&sort_order=asc")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Not authenticated"}

    response = client.get(f"/applications/id/{appid}", headers=admin_header)
    assert_ok(response)

    response = client.get(f"/applications/id/{appid}", headers=lender_header)
    assert_ok(response)

    response = client.get(f"/applications/id/{appid}")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Not authenticated"}

    # tries to get a non existing application
    response = client.get("/applications/id/999", headers=lender_header)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Application not found"}

    response = client.get("/applications", headers=lender_header)
    assert_ok(response)

    response = client.get("/applications")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Not authenticated"}

    response = client.get("/applications/uuid/123-456-789")
    assert_ok(response)

    pending_application.status = models.ApplicationStatus.LAPSED
    session.commit()

    response = client.get("/applications/uuid/123-456-789")
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "APPLICATION_LAPSED"}

    response = client.get("/applications/uuid/123-456")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Application not found"}

    response = client.post("/applications/access-scheme", json={"uuid": "123-456"})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Application not found"}


def test_application_declined(client, pending_application):
    response = client.post(
        "/applications/decline", json={"uuid": "123-456-789", "decline_this": False, "decline_all": True}
    )

    assert_ok(response)
    assert response.json()["application"]["status"] == models.ApplicationStatus.DECLINED
    assert response.json()["borrower"]["status"] == models.BorrowerStatus.DECLINE_OPPORTUNITIES

    response = client.post("/applications/access-scheme", json={"uuid": "123-456-789"})

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "Application status should not be DECLINED"}


def test_application_rollback_declined(client, session, declined_application):
    declined_application.borrower.status = models.BorrowerStatus.DECLINE_OPPORTUNITIES
    session.commit()

    response = client.post("/applications/rollback-decline", json={"uuid": "123-456-789"})

    assert_ok(response)
    assert response.json()["application"]["status"] == models.ApplicationStatus.PENDING
    assert response.json()["borrower"]["status"] == models.BorrowerStatus.ACTIVE

    response = client.post("/applications/rollback-decline", json={"uuid": "123-456-789"})

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "Application status should not be PENDING"}


def test_application_declined_feedback(client, declined_application):
    declined_feedback_payload = {
        "uuid": "123-456-789",
        "dont_need_access_credit": True,
        "already_have_acredit": False,
        "preffer_to_go_to_bank": False,
        "dont_want_access_credit": False,
        "other": False,
        "other_comments": "comments",
    }

    response = client.post("/applications/decline-feedback", json=declined_feedback_payload)

    assert_ok(response)
    assert response.json()["application"]["status"] == models.ApplicationStatus.DECLINED
    declined_feedback_payload.pop("uuid")
    assert response.json()["application"]["borrower_declined_preferences_data"] == declined_feedback_payload
