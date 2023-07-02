from fastapi import status

import tests.test_client as test_client

from tests.test_client import app, client  # isort:skip # noqa
from tests.test_client import mock_cognito_client, mock_ses_client  # isort:skip # noqa

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
    OCP_headers = test_client.create_test_user(client, test_client.OCP_user)
    FI_headers = test_client.create_test_user(client, test_client.FI_user)

    response = client.post("/lenders/", json=lender, headers=OCP_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.post("/lenders/", json=lender, headers=FI_headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_lender(client):  # isort:skip # noqa
    OCP_headers = test_client.create_test_user(client, test_client.OCP_user)
    FI_headers = test_client.create_test_user(client, test_client.FI_user)

    response = client.post("/lenders/", json=lender, headers=OCP_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/lenders/", headers=OCP_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/lenders/1", headers=FI_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/lenders/100", headers=OCP_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_lender(client):  # isort:skip # noqa
    OCP_headers = test_client.create_test_user(client, test_client.OCP_user)
    FI_headers = test_client.create_test_user(client, test_client.FI_user)

    response = client.post("/lenders/", json=lender, headers=OCP_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.put("/lenders/1", json=lender_modified, headers=OCP_headers)
    assert response.json()["name"] == lender_modified["name"]
    assert response.status_code == status.HTTP_200_OK

    response = client.put("/lenders/1", json=lender_modified, headers=FI_headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
