from fastapi import status

from app.models import BorrowerSize, CreditType, UserType

FI_user = {
    "email": "FI_user@noreply.open-contracting.org",
    "name": "Test FI",
    "type": UserType.FI,
}

OCP_user = {
    "email": "OCP_user@noreply.open-contracting.org",
    "name": "OCP_user@example.com",
    "type": UserType.OCP,
}

lender = {
    "name": "John Doe",
    "email_group": "lenders@noreply.open-contracting.org",
    "status": "Active",
    "type": "Some Type",
    "borrowed_type_preferences": {},
    "limits_preferences": {},
    "sla_days": 5,
}

lender_modified = {
    "name": "John smith",
    "email_group": "lenders@noreply.open-contracting.org",
    "status": "Active",
    "type": "Some Type",
    "borrowed_type_preferences": {},
    "limits_preferences": {},
    "sla_days": 5,
}

lender_modified_not_valid = {
    "sla_days": "not_valid_value",
}

credit_product = {
    "borrower_size": BorrowerSize.SMALL,
    "lower_limit": 10000.00,
    "upper_limit": 50000.00,
    "interest_rate": "The interest rate of the credit lines is variable and is subject to...",
    "required_document_types": {
        "INCORPORATION_DOCUMENT": True,
        "FINANCIAL_STATEMENT": True,
        "SUPPLIER_REGISTRATION_DOCUMENT": True,
    },
    "type": CreditType.CREDIT_LINE,
    "other_fees_total_amount": 100,
    "other_fees_description": "Processing fee",
    "more_info_url": "https://example.com",
    "lender_id": 1,
}

updated_credit_product = {
    "borrower_size": BorrowerSize.SMALL,
    "lower_limit": 100000.00,
    "upper_limit": 500000.00,
    "interest_rate": "The interest rate of the credit lines is variable and is subject to...",
    "required_document_types": {
        "INCORPORATION_DOCUMENT": True,
        "FINANCIAL_STATEMENT": True,
        "SUPPLIER_REGISTRATION_DOCUMENT": True,
    },
    "type": CreditType.CREDIT_LINE,
    "other_fees_total_amount": 100,
    "other_fees_description": "Processing fee",
    "more_info_url": "https://example.com",
    "lender_id": 1,
}

lender_with_credit_product = {
    "name": "test lender",
    "email_group": "test@noreply.open-contracting.org",
    "status": "Active",
    "type": "Some Type",
    "sla_days": 5,
    "credit_products": [
        {
            "borrower_size": "SMALL",
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
            "lender_id": 1,
        }
    ],
}


def test_create_credit_product(client):
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    FI_headers = client.post("/create-test-user-headers", json=FI_user).json()

    client.post("/lenders", json=lender, headers=OCP_headers)

    # FI tries to create credit product
    response = client.post("/lenders/1/credit-products", json=credit_product, headers=FI_headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    response = client.post("/lenders/1/credit-products", json=credit_product, headers=OCP_headers)
    assert response.status_code == status.HTTP_200_OK

    # OCP user tries to create a credit product for a non existent lender
    response = client.post("/lenders/100/credit-products", json=credit_product, headers=OCP_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND

    response = client.put("/credit-products/1", json=updated_credit_product, headers=OCP_headers)
    assert response.json()["lower_limit"] == updated_credit_product["lower_limit"]
    assert response.json()["upper_limit"] == updated_credit_product["upper_limit"]
    assert response.status_code == status.HTTP_200_OK

    # tries to update a credit product that does not exist
    response = client.put("/credit-products/100", json=updated_credit_product, headers=OCP_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND

    response = client.get("/credit-products/1")
    assert response.status_code == status.HTTP_200_OK


def test_create_lender(client):
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    FI_headers = client.post("/create-test-user-headers", json=FI_user).json()

    response = client.post("/lenders/", json=lender, headers=OCP_headers)
    assert response.status_code == status.HTTP_200_OK

    # tries to create same lender twice
    response = client.post("/lenders/", json=lender, headers=OCP_headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    response = client.post("/lenders/", json=lender, headers=FI_headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_lender_with_credit_product(client):
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    FI_headers = client.post("/create-test-user-headers", json=FI_user).json()

    response = client.post("/lenders/", json=lender_with_credit_product, headers=OCP_headers)
    assert response.status_code == status.HTTP_200_OK

    # fi user tries to create lender
    response = client.post("/lenders/", json=lender_with_credit_product, headers=FI_headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_lender(client):
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    FI_headers = client.post("/create-test-user-headers", json=FI_user).json()

    response = client.post("/lenders/", json=lender, headers=OCP_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/lenders/", headers=OCP_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/lenders/1", headers=FI_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/lenders/100", headers=OCP_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_lender(client):
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    FI_headers = client.post("/create-test-user-headers", json=FI_user).json()

    response = client.post("/lenders/", json=lender, headers=OCP_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.put("/lenders/1", json=lender_modified, headers=OCP_headers)
    assert response.json()["name"] == lender_modified["name"]
    assert response.status_code == status.HTTP_200_OK

    # fi user tries to update lender
    response = client.put("/lenders/1", json=lender_modified, headers=FI_headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    response = client.put("/lenders/1", json=lender_modified_not_valid, headers=OCP_headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
