import warnings

from fastapi import status

from app.models import BorrowerSize, CreditType, UserType

lender_user = {
    "email": "lender-user@noreply.open-contracting.org",
    "name": "Test lender",
    "type": UserType.FI,
}

ocp_user = {
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
    ocp_headers = client.post("/create-test-user-headers", json=ocp_user).json()
    lender_headers = client.post("/create-test-user-headers", json=lender_user).json()

    client.post("/lenders", json=lender, headers=ocp_headers)

    # Lender tries to create credit product
    response = client.post("/lenders/1/credit-products", json=credit_product, headers=lender_headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    with warnings.catch_warnings():
        # "Pydantic serializer warnings" "Expected `decimal` but got `float` - serialized value may not be as expected"
        warnings.filterwarnings("ignore")

        response = client.post("/lenders/1/credit-products", json=credit_product, headers=ocp_headers)
        assert response.json()["lender_id"] == 1
        assert response.status_code == status.HTTP_200_OK

    # OCP user tries to create a credit product for a non existent lender
    response = client.post("/lenders/999/credit-products", json=credit_product, headers=ocp_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND

    with warnings.catch_warnings():
        # "Pydantic serializer warnings" "Expected `decimal` but got `int` - serialized value may not be as expected"
        warnings.filterwarnings("ignore")

        response = client.put("/credit-products/1", json=updated_credit_product, headers=ocp_headers)
        assert response.json()["lower_limit"] == updated_credit_product["lower_limit"]
        assert response.json()["upper_limit"] == updated_credit_product["upper_limit"]
        assert response.json()["other_fees_description"] == updated_credit_product["other_fees_description"]
        assert response.status_code == status.HTTP_200_OK

    # tries to update a credit product that does not exist
    response = client.put("/credit-products/999", json=updated_credit_product, headers=ocp_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND

    response = client.get("/credit-products/1")
    assert response.status_code == status.HTTP_200_OK


def test_create_lender(client):
    ocp_headers = client.post("/create-test-user-headers", json=ocp_user).json()
    lender_headers = client.post("/create-test-user-headers", json=lender_user).json()

    response = client.post("/lenders/", json=lender, headers=ocp_headers)
    assert response.json()["id"] == 1
    assert response.status_code == status.HTTP_200_OK

    # tries to create same lender twice
    response = client.post("/lenders/", json=lender, headers=ocp_headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    response = client.post("/lenders/", json=lender, headers=lender_headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_lender_with_credit_product(client):
    ocp_headers = client.post("/create-test-user-headers", json=ocp_user).json()
    lender_headers = client.post("/create-test-user-headers", json=lender_user).json()

    with warnings.catch_warnings():
        # "Pydantic serializer warnings" "Expected `decimal` but got `float` - serialized value may not be as expected"
        warnings.filterwarnings("ignore")

        response = client.post("/lenders/", json=lender_with_credit_product, headers=ocp_headers)
        assert response.status_code == status.HTTP_200_OK

    # lender user tries to create lender
    response = client.post("/lenders/", json=lender_with_credit_product, headers=lender_headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_lender(client):
    ocp_headers = client.post("/create-test-user-headers", json=ocp_user).json()
    lender_headers = client.post("/create-test-user-headers", json=lender_user).json()

    response = client.post("/lenders/", json=lender, headers=ocp_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/lenders/", headers=ocp_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/lenders/1", headers=lender_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/lenders/999", headers=ocp_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_lender(client):
    ocp_headers = client.post("/create-test-user-headers", json=ocp_user).json()
    lender_headers = client.post("/create-test-user-headers", json=lender_user).json()

    response = client.post("/lenders/", json=lender, headers=ocp_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.put("/lenders/1", json=lender_modified, headers=ocp_headers)
    assert response.json()["name"] == lender_modified["name"]
    assert response.status_code == status.HTTP_200_OK

    # Lender user tries to update lender
    response = client.put("/lenders/1", json=lender_modified, headers=lender_headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    response = client.put("/lenders/1", json=lender_modified_not_valid, headers=ocp_headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
