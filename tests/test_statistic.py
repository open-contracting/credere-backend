from fastapi import status

from app import models
from app.utils.statistics import update_statistics
from tests.common import common_test_client

from tests.common.common_test_client import start_background_db  # isort:skip # noqa
from tests.common.common_test_client import mock_ses_client  # isort:skip # noqa
from tests.common.common_test_client import mock_cognito_client  # isort:skip # noqa
from tests.common.common_test_client import app, client  # isort:skip # noqa

OCP_user = {
    "email": "OCP_user@example.com",
    "name": "OCP_user@example.com",
    "type": models.UserType.OCP.value,
}
lender = {
    "id": 1,
    "name": "test",
    "email_group": "test@lender.com",
    "status": "Active",
    "type": "Some Type",
    "sla_days": 7,
}
FI_user_with_lender = {
    "id": 2,
    "email": "FI_user_with_lender@example.com",
    "name": "Test FI with lender",
    "type": models.UserType.FI.value,
    "lender_id": 1,
}


def test_update_statistic(start_background_db):  # noqa
    update_statistics(common_test_client.get_test_db)


def test_statistics(client):  # noqa
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    client.post("/lenders", json=lender, headers=OCP_headers)
    FI_headers = client.post("/create-test-user-headers", json=FI_user_with_lender).json()
    response = client.get("/statistics-ocp", headers=OCP_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/statistics-ocp/opt-in", headers=OCP_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/statistics-fi", headers=FI_headers)
    assert response.status_code == status.HTTP_200_OK
