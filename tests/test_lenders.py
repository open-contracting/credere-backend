from fastapi import status
from tests.common.utils import OCP_user, FI_user
from tests.common.common_test_client import mock_ses_client  # isort:skip # noqa

from tests.common.common_test_client import mock_cognito_client  # isort:skip # noqa

from tests.common.common_test_client import app, client  # isort:skip # noqa

lender = {
    "name": "John Doe",
    "email_group": "lenders@example.com",
    "status": "Active",
    "type": "Some Type",
    "borrowed_type_preferences": {},
    "limits_preferences": {},
    "sla_days": 5,
}

lender_modified = {
    "name": "John smith",
    "email_group": "lenders@example.com",
    "status": "Active",
    "type": "Some Type",
    "borrowed_type_preferences": {},
    "limits_preferences": {},
    "sla_days": 5,
}


def test_create_lender(client):  # isort:skip # noqa
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    FI_headers = client.post("/create-test-user-headers", json=FI_user).json()

    response = client.post("/lenders/", json=lender, headers=OCP_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.post("/lenders/", json=lender, headers=FI_headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_lender(client):  # isort:skip # noqa
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


def test_update_lender(client):  # isort:skip # noqa
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    FI_headers = client.post("/create-test-user-headers", json=FI_user).json()

    response = client.post("/lenders/", json=lender, headers=OCP_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.put("/lenders/1", json=lender_modified, headers=OCP_headers)
    assert response.json()["name"] == lender_modified["name"]
    assert response.status_code == status.HTTP_200_OK

    response = client.put("/lenders/1", json=lender_modified, headers=FI_headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
