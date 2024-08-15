from fastapi import status

from app import models
from app.commands import update_statistics

ocp_user = {
    "email": "OCP-user@example.com",
    "name": "OCP-user@example.com",
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
lender_user = {
    "id": 2,
    "email": "lender-user@example.com",
    "name": "Test lender",
    "type": models.UserType.FI,
    "lender_id": 1,
}


def test_update_statistic(engine, create_and_drop_database):
    update_statistics()


def test_statistics(client):
    ocp_headers = client.post("/create-test-user-headers", json=ocp_user).json()
    client.post("/lenders", json=lender, headers=ocp_headers)
    lender_headers = client.post("/create-test-user-headers", json=lender_user).json()
    response = client.get("/statistics-ocp", headers=ocp_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/statistics-ocp/opt-in", headers=ocp_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/statistics-fi", headers=lender_headers)
    assert response.status_code == status.HTTP_200_OK
