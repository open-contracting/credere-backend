import uuid
import warnings

from fastapi import status

from app import models
from app.i18n import _
from tests import assert_ok


def test_create_credit_product(client, admin_header, lender_header, lender):
    create_payload = {
        "borrower_size": models.BorrowerSize.SMALL,
        "lower_limit": 10000.00,
        "upper_limit": 50000.00,
        "interest_rate": "The interest rate of the credit lines is variable and is subject to...",
        "required_document_types": {
            "INCORPORATION_DOCUMENT": True,
            "FINANCIAL_STATEMENT": True,
            "SUPPLIER_REGISTRATION_DOCUMENT": True,
        },
        "type": models.CreditType.CREDIT_LINE,
        "other_fees_total_amount": 100,
        "other_fees_description": "Processing fee",
        "more_info_url": "https://example.com",
        "lender_id": lender.id,
    }
    update_payload = {
        "borrower_size": models.BorrowerSize.SMALL,
        "lower_limit": 100000.00,
        "upper_limit": 500000.00,
        "interest_rate": "The interest rate of the credit lines is variable and is subject to...",
        "required_document_types": {
            "INCORPORATION_DOCUMENT": True,
            "FINANCIAL_STATEMENT": True,
            "SUPPLIER_REGISTRATION_DOCUMENT": True,
        },
        "type": models.CreditType.CREDIT_LINE,
        "other_fees_total_amount": 100,
        "other_fees_description": "Transaction fee",
        "more_info_url": "https://example.com",
        "lender_id": lender.id,
    }

    # Lender tries to create credit product
    response = client.post(f"/lenders/{lender.id}/credit-products", json=create_payload, headers=lender_header)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": _("Insufficient permissions")}

    with warnings.catch_warnings():
        # "Pydantic serializer warnings" "Expected `decimal` but got `float` - serialized value may not be as expected"
        warnings.filterwarnings("ignore")

        response = client.post(f"/lenders/{lender.id}/credit-products", json=create_payload, headers=admin_header)
        assert_ok(response)
        assert response.json()["lender_id"] == lender.id
        credit_product_id = response.json()["id"]

    # OCP user tries to create a credit product for a non existent lender
    response = client.post("/lenders/999/credit-products", json=create_payload, headers=admin_header)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": _("%(model_name)s not found", model_name="Lender")}

    with warnings.catch_warnings():
        # "Pydantic serializer warnings" "Expected `decimal` but got `int` - serialized value may not be as expected"
        warnings.filterwarnings("ignore")

        response = client.put(f"/credit-products/{credit_product_id}", json=update_payload, headers=admin_header)
        assert_ok(response)
        assert response.json()["lower_limit"] == 100000.00
        assert response.json()["upper_limit"] == 500000.00
        assert response.json()["other_fees_description"] == "Transaction fee"

    # tries to update a credit product that does not exist
    response = client.put("/credit-products/999", json=update_payload, headers=admin_header)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": _("%(model_name)s not found", model_name="CreditProduct")}

    response = client.get(f"/credit-products/{credit_product_id}")
    assert_ok(response)


def test_create_lender(client, admin_header, lender_header, lender):
    payload = {
        "name": str(uuid.uuid4()),
        "email_group": "lenders@noreply.open-contracting.org",
        "type": "Some Type",
        "sla_days": 5,
    }

    response = client.post("/lenders", json=payload, headers=admin_header)
    assert_ok(response)
    assert response.json()["id"] == lender.id + 1

    # tries to create same lender twice
    response = client.post("/lenders", json=payload, headers=admin_header)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": _("Lender with that name already exists")}

    response = client.post("/lenders", json=payload, headers=lender_header)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": _("Insufficient permissions")}


def test_create_lender_with_credit_product(client, admin_header, lender_header, lender):
    payload = {
        "name": str(uuid.uuid4()),
        "email_group": "test@noreply.open-contracting.org",
        "type": "Some Type",
        "sla_days": 5,
        "credit_products": [
            {
                "borrower_size": models.BorrowerSize.SMALL,
                "lower_limit": 10000.00,
                "upper_limit": 50000.00,
                "interest_rate": "The interest rate of the credit lines is variable and is subject to...",
                "required_document_types": {
                    "INCORPORATION_DOCUMENT": True,
                    "FINANCIAL_STATEMENT": True,
                    "SUPPLIER_REGISTRATION_DOCUMENT": True,
                },
                "type": "CREDIT_LINE",
                "other_fees_total_amount": 100,
                "other_fees_description": "Processing fee",
                "more_info_url": "https://example.com",
                "lender_id": lender.id,
            }
        ],
    }

    with warnings.catch_warnings():
        # "Pydantic serializer warnings" "Expected `decimal` but got `float` - serialized value may not be as expected"
        warnings.filterwarnings("ignore")

        response = client.post("/lenders", json=payload, headers=admin_header)
        assert_ok(response)

    # lender user tries to create lender
    response = client.post("/lenders", json=payload, headers=lender_header)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": _("Insufficient permissions")}


def test_get_lender(client, admin_header, lender_header, unauthorized_lender_header, lender):
    response = client.get("/lenders", headers=admin_header)
    assert_ok(response)

    response = client.get(f"/lenders/{lender.id}", headers=lender_header)
    assert_ok(response)

    response = client.get(f"/lenders/{lender.id}", headers=unauthorized_lender_header)
    assert_ok(response)

    response = client.get("/lenders/999", headers=admin_header)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": _("%(model_name)s not found", model_name="Lender")}


def test_update_lender(client, admin_header, lender_header, lender):
    payload = {
        "name": str(uuid.uuid4()),
        "email_group": "lenders@noreply.open-contracting.org",
        "type": "Some Type",
        "sla_days": 5,
    }

    response = client.put(f"/lenders/{lender.id}", json=payload, headers=admin_header)
    assert_ok(response)
    assert response.json()["name"] == payload["name"]

    # Lender user tries to update lender
    response = client.put(f"/lenders/{lender.id}", json=payload, headers=lender_header)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": _("Insufficient permissions")}

    response = client.put(f"/lenders/{lender.id}", json={"sla_days": "not_valid_value"}, headers=admin_header)
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert data == {
        "detail": [
            {
                "input": "not_valid_value",
                "loc": ["body", "sla_days"],
                "msg": "Input should be a valid integer, unable to parse string as an integer",
                "type": "int_parsing",
            }
        ],
    }
