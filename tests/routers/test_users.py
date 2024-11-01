import datetime
import uuid

import pytest
from fastapi import status

from app.i18n import _
from tests import assert_ok


def test_get_me(client, admin_header):
    response = client.get("/users/me", headers=admin_header)
    assert_ok(response)
    assert response.json()["user"]["name"] == "OCP Test User"


@pytest.mark.parametrize("with_lender", [True, False])
def test_create_and_get_user(client, admin_header, lender_header, user_payload, lender, with_lender):
    lender_id = lender.id if with_lender else None

    response = client.post("/users", json=user_payload | {"lender_id": lender_id}, headers=admin_header)
    assert_ok(response)
    assert response.json()["name"] == user_payload["name"]
    assert response.json()["lender_id"] == lender_id

    # fetch second user since the first one is the OCP user created for headers
    response = client.get("/users/2", headers=admin_header)
    assert_ok(response)

    # try to get a non-existing user
    response = client.get("/users/200", headers=admin_header)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": _("%(model_name)s not found", model_name="User")}

    # try to get all users
    response = client.get("/users?page=0&page_size=5&sort_field=created_at&sort_order=desc", headers=admin_header)
    assert_ok(response)

    response = client.get("/users?page=0&page_size=5&sort_field=created_at&sort_order=desc", headers=lender_header)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": _("Insufficient permissions")}


def test_update_user(client, admin_header, lender_header, user_payload):
    new_email = f"new-name-{uuid.uuid4()}@example.com"

    response = client.post("/users", json=user_payload, headers=admin_header)
    data = response.json()
    user_id = data["id"]

    assert_ok(response)
    assert data["name"] == user_payload["name"]

    response = client.put(f"/users/{user_id}", json={"email": new_email}, headers=admin_header)
    assert_ok(response)
    assert response.json()["email"] == new_email

    response = client.put(f"/users/{user_id}", json={"email": "another-email@example.com"}, headers=lender_header)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": _("Insufficient permissions")}


def test_duplicate_user(client, admin_header, user_payload):
    response = client.post("/users", json=user_payload, headers=admin_header)
    assert_ok(response)

    # duplicate user
    response = client.post("/users", json=user_payload, headers=admin_header)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": _("User with that email already exists")}


def test_login(client, admin_header, admin_email):
    client.get("/users/logout", headers=admin_header)
    response = client.post(
        "/users/login",
        json={
            "username": admin_email,
            "password": "12345-UPPER-lower",
            "temp_password": "123456",
        },
    )
    data = response.json()
    user = data.pop("user")
    user_id = user.pop("id")
    created_at = user.pop("created_at")

    assert len(data) == 2
    assert isinstance(user_id, int)
    assert datetime.datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S.%f%z")
    assert user == {
        "email": admin_email,
        "external_id": admin_email,
        "language": "es",
        "lender_id": None,
        "name": "OCP Test User",
        "notification_preferences": {},
        "type": "OCP",
    }
    assert isinstance(data["access_token"], str)
    assert isinstance(data["refresh_token"], str)
    assert response.status_code == status.HTTP_200_OK


def test_login_invalid_username(client):
    response = client.post("/users/login", json={"username": "nonexistent", "password": "", "temp_password": ""})

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": _("Invalid username or password")}


# UserCode is not implemented yet in moto, so can't test invalid MFA.
def test_login_invalid_password(client, admin_header, admin_email):
    client.get("/users/logout", headers=admin_header)
    response = client.post(
        "/users/login",
        json={
            "username": admin_email,
            "password": "invalid",
            "temp_password": "123456",
        },
    )

    assert response.json() == {"detail": _("Invalid username or password")}
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_logout(client, admin_header):
    response = client.get("/users/logout", headers=admin_header)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"detail": _("User logged out successfully")}


def test_logout_invalid_authorization_header_no_period(client):
    response = client.get("/users/logout", headers={"Authorization": "Bearer ACCESS_TOKEN"})

    assert_ok(response)
    assert response.json() == {"detail": _("User logged out successfully")}


def test_logout_invalid_authorization_header(client):
    response = client.get("/users/logout", headers={"Authorization": "Bearer ACCESS.TOKEN"})

    assert_ok(response)
    assert response.json() == {"detail": _("User logged out successfully")}


def test_logout_no_authorization_header(client):
    response = client.get("/users/logout")

    assert_ok(response)
    assert response.json() == {"detail": _("User logged out successfully")}
