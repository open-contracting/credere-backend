from fastapi import status

from app import models
from app.utils.statistics import update_statistics
from tests import get_test_db

ocp_user = {
    "email": "OCP_user@example.com",
    "name": "OCP_user@example.com",
    "type": models.UserType.OCP,
}
lender = {
    "id": 1,
    "name": "test",
    "email_group": "test@lender.com",
    "status": "Active",
    "type": "Some Type",
    "sla_days": 7,
}
fi_user_with_lender = {
    "id": 2,
    "email": "FI_user_with_lender@example.com",
    "name": "Test FI with lender",
    "type": models.UserType.FI,
    "lender_id": 1,
}


def test_update_statistic(engine, create_and_drop_database):
    update_statistics(get_test_db(engine))


def test_statistics(client):
    ocp_headers = client.post("/create-test-user-headers", json=ocp_user).json()
    client.post("/lenders", json=lender, headers=ocp_headers)
    fi_headers = client.post("/create-test-user-headers", json=fi_user_with_lender).json()
    response = client.get("/statistics-ocp", headers=ocp_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/statistics-ocp/opt-in", headers=ocp_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/statistics-fi", headers=fi_headers)
    assert response.status_code == status.HTTP_200_OK
