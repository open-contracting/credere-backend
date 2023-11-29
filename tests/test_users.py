from fastapi import status

from app.models import UserType

from tests.common.common_test_client import mock_ses_client  # isort:skip # noqa
from tests.common.common_test_client import mock_cognito_client  # isort:skip # noqa
from tests.common.common_test_client import app, client  # isort:skip # noqa

OCP_user = {
    "email": "OCP_test@noreply.open-contracting.org",
    "name": "OCP Test User",
    "type": UserType.OCP.value,
}
FI_user = {
    "email": "fi_test@noreply.open-contracting.org",
    "name": "FI Test User",
    "type": UserType.FI.value,
}

test_user = {
    "email": "test@noreply.open-contracting.org",
    "name": "Test User",
    "type": UserType.FI.value,
}


def test_get_me(client):  # noqa
    ocp_headers = client.post("/create-test-user-headers", json=OCP_user).json()

    response = client.get("/users/me", headers=ocp_headers)
    assert response.json()["user"]["name"] == OCP_user["name"]
    assert response.status_code == status.HTTP_200_OK


def test_create_and_get_user(client):  # noqa
    ocp_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    fi_headers = client.post("/create-test-user-headers", json=FI_user).json()

    response = client.post("/users", json=test_user, headers=ocp_headers)
    assert response.status_code == status.HTTP_200_OK

    # fetch second user since the first one is the OCP user created for headers
    response = client.get("/users/2")
    assert response.status_code == status.HTTP_200_OK

    # try to get a non-existing user
    response = client.get("/users/200")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # try to get all users
    response = client.get(
        "/users?page=0&page_size=5&sort_field=credere_user_created_at&sort_order=desc",
        headers=ocp_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.get(
        "/users?page=0&page_size=5&sort_field=credere_user_created_at&sort_order=desc",
        headers=fi_headers,
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_update_user(client):  # noqa
    ocp_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    fi_headers = client.post("/create-test-user-headers", json=FI_user).json()

    response = client.post("/users", json=test_user, headers=ocp_headers)
    assert response.json()["name"] == test_user["name"]
    assert response.status_code == status.HTTP_200_OK

    # update user 3 since 1 is ocp test user and 2 FI test user
    response = client.put(
        "/users/3",
        json={"email": "new_name@noreply.open-contracting.org"},
        headers=ocp_headers,
    )
    assert response.json()["email"] == "new_name@noreply.open-contracting.org"
    assert response.status_code == status.HTTP_200_OK

    response = client.put(
        "/users/3",
        json={"email": "anoter_email@noreply.open-contracting.org"},
        headers=fi_headers,
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_duplicate_user(client):  # noqa
    ocp_headers = client.post("/create-test-user-headers", json=OCP_user).json()

    response = client.post("/users", json=test_user, headers=ocp_headers)
    assert response.status_code == status.HTTP_200_OK
    # duplicate user
    response = client.post("/users", json=test_user, headers=ocp_headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
