import logging
import uuid

from fastapi import status

from app.i18n import _
from tests import assert_ok


def test_get_me(client, admin_header):
    response = client.get("/users/me", headers=admin_header)
    assert_ok(response)
    assert response.json()["user"]["name"] == "OCP Test User"


def test_create_and_get_user(client, admin_header, lender_header, user_payload):
    response = client.post("/users", json=user_payload, headers=admin_header)
    assert_ok(response)
    assert response.json()["name"] == user_payload["name"]

    # fetch second user since the first one is the OCP user created for headers
    response = client.get("/users/2")
    assert_ok(response)

    # try to get a non-existing user
    response = client.get("/users/200")
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


def test_logout(client, admin_header, caplog):
    caplog.set_level(logging.ERROR)

    response = client.get("/users/logout", headers=admin_header)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"detail": "User logged out successfully"}
    assert not caplog.records


def test_logout_invalid_authorization_header(client, caplog):
    caplog.set_level(logging.ERROR)

    response = client.get("/users/logout", headers={"Authorization": "Bearer ACCESS_TOKEN"})

    assert_ok(response)
    assert response.json() == {"detail": _("User logged out successfully")}
    assert not caplog.records


def test_logout_no_authorization_header(client, caplog):
    caplog.set_level(logging.ERROR)

    response = client.get("/users/logout")

    assert_ok(response)
    assert response.json() == {"detail": _("User logged out successfully")}
    assert not caplog.records
