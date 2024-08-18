from datetime import datetime, timedelta

from fastapi import status

from app import models
from tests import assert_ok


def test_application_declined(client, pending_application):
    response = client.post(
        "/applications/decline", json={"uuid": pending_application.uuid, "decline_this": False, "decline_all": True}
    )

    assert_ok(response)
    assert response.json()["application"]["status"] == models.ApplicationStatus.DECLINED
    assert response.json()["borrower"]["status"] == models.BorrowerStatus.DECLINE_OPPORTUNITIES

    response = client.post("/applications/access-scheme", json={"uuid": pending_application.uuid})

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "Application status should not be DECLINED"}


def test_application_rollback_declined(client, session, declined_application):
    declined_application.borrower.status = models.BorrowerStatus.DECLINE_OPPORTUNITIES
    session.commit()

    response = client.post("/applications/rollback-decline", json={"uuid": declined_application.uuid})

    assert_ok(response)
    assert response.json()["application"]["status"] == models.ApplicationStatus.PENDING
    assert response.json()["borrower"]["status"] == models.BorrowerStatus.ACTIVE

    response = client.post("/applications/rollback-decline", json={"uuid": declined_application.uuid})

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "Application status should not be PENDING"}


def test_application_declined_feedback(client, declined_application):
    declined_feedback_payload = {
        "uuid": declined_application.uuid,
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


def test_access_expired_application(client, session, pending_application):
    pending_application.expired_at = datetime.now(pending_application.created_at.tzinfo) - timedelta(days=+1)
    session.commit()

    # borrower tries to access expired application
    response = client.get(f"/applications/uuid/{pending_application.uuid}")

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "Application expired"}


def test_rollback_credit_product(client, accepted_application):
    response = client.post(
        "/applications/rollback-select-credit-product",
        json={
            "uuid": accepted_application.uuid,
            "borrower_size": models.BorrowerSize.SMALL,
            "amount_requested": 10000,
            "sector": "adminstration",
            "credit_product_id": accepted_application.credit_product_id,
        },
    )

    assert_ok(response)
    assert response.json()["application"]["uuid"] == accepted_application.uuid
    assert response.json()["application"]["credit_product_id"] is None
    assert response.json()["application"]["borrower_credit_product_selected_at"] is None
