import logging

from fastapi import status

import tests.test_client as test_client
from app.schema.core import UserType

from tests.test_client import app, client  # isort:skip # noqa
from tests.test_client import mock_cognito_client, mock_ses_client  # isort:skip # noqa

data = {"email": "test@example.com", "name": "Test User", "type": UserType.FI.value}


def test_create_user(client):  # isort:skip # noqa
    response = client.post("/users", json=data)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/users/1")
    assert response.status_code == status.HTTP_200_OK


def test_duplicate_user(client):  # isort:skip # noqa
    response = client.post("/users", json=data)
    assert response.status_code == status.HTTP_200_OK
    # duplicate user
    response = client.post("/users", json=data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_login(client):  # isort:skip # noqa
    responseCreate = client.post("/users", json=data)
    assert responseCreate.status_code == status.HTTP_200_OK

    setupPasswordPayload = {
        "username": data["email"],
        "temp_password": test_client.tempPassword,
        "password": test_client.tempPassword,
    }
    responseSetupPassword = client.put(
        "/users/change-password", json=setupPasswordPayload
    )
    logging.info(responseSetupPassword.json())
    assert responseSetupPassword.status_code == status.HTTP_200_OK

    loginPayload = {"username": data["email"], "password": test_client.tempPassword}
    responseLogin = client.post("/users/login", json=loginPayload)
    logging.info(responseLogin.json())

    assert responseLogin.status_code == status.HTTP_200_OK
    assert responseLogin.json()["access_token"] is not None

    responseAccessProtectedRoute = client.get(
        "/secure-endpoint-example",
        headers={"Authorization": "Bearer " + responseLogin.json()["access_token"]},
    )
    logging.info(responseAccessProtectedRoute.json())

    assert responseAccessProtectedRoute.status_code == status.HTTP_200_OK
    assert (
        responseAccessProtectedRoute.json()["message"] is not None
        and responseAccessProtectedRoute.json()["message"] == "OK"
    )

    responseAccessProtectedRouteWithUser = client.get(
        "/secure-endpoint-example-username-extraction",
        headers={"Authorization": "Bearer " + responseLogin.json()["access_token"]},
    )
    logging.info(responseAccessProtectedRouteWithUser.json())

    assert responseAccessProtectedRouteWithUser.status_code == status.HTTP_200_OK
    logging.info(responseAccessProtectedRouteWithUser.json())
    assert (
        responseAccessProtectedRouteWithUser.json()["username"]
        == setupPasswordPayload["username"]
    )
