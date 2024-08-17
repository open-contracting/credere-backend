import logging

from fastapi import status

from app.models import UserType
from tests import assert_ok

payload = {
    "email": "test@noreply.open-contracting.org",
    "name": "Test User",
    "type": UserType.FI,
}


def test_get_me(client, admin_header):
    response = client.get("/users/me", headers=admin_header)
    assert_ok(response)
    assert response.json()["user"]["name"] == "OCP Test User"


def test_create_and_get_user(client, admin_header, lender_header):
    response = client.post("/users", json=payload, headers=admin_header)
    assert_ok(response)
    assert response.json()["name"] == payload["name"]

    # fetch second user since the first one is the OCP user created for headers
    response = client.get("/users/2")
    assert_ok(response)

    # try to get a non-existing user
    response = client.get("/users/200")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "User not found"}

    # try to get all users
    response = client.get(
        "/users?page=0&page_size=5&sort_field=created_at&sort_order=desc",
        headers=admin_header,
    )
    assert_ok(response)

    response = client.get(
        "/users?page=0&page_size=5&sort_field=created_at&sort_order=desc",
        headers=lender_header,
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Insufficient permissions"}


def test_update_user(client, admin_header, lender_header):
    response = client.post("/users", json=payload, headers=admin_header)
    assert_ok(response)
    assert response.json()["name"] == payload["name"]

    # update user 3 since 1 is ocp test user and 2 lender test user
    response = client.put(
        "/users/3",
        json={"email": "new_name@noreply.open-contracting.org"},
        headers=admin_header,
    )
    assert_ok(response)
    assert response.json()["email"] == "new_name@noreply.open-contracting.org"

    response = client.put(
        "/users/3",
        json={"email": "anoter_email@noreply.open-contracting.org"},
        headers=lender_header,
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Insufficient permissions"}


def test_duplicate_user(client, admin_header):
    response = client.post("/users", json=payload, headers=admin_header)
    assert_ok(response)

    # duplicate user
    response = client.post("/users", json=payload, headers=admin_header)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json() == {"detail": "Username already exists"}


def test_logout_invalid_authorization_header(client, caplog):
    caplog.set_level(logging.ERROR)

    response = client.get("/users/logout", headers={"Authorization": "Bearer ACCESS_TOKEN"})

    assert_ok(response)
    assert response.json() == {"detail": "User logged out successfully"}
    assert not caplog.records


def test_logout_no_authorization_header(client, caplog):
    caplog.set_level(logging.ERROR)

    response = client.get("/users/logout")

    assert_ok(response)
    assert response.json() == {"detail": "User logged out successfully"}
    assert not caplog.records
