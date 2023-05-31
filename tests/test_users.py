from typing import Any, Generator

import boto3
import pytest
from botocore.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from moto import mock_cognitoidp, mock_ses
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.settings import app_settings
from app.core.user_dependencies import CognitoClient, get_cognito_client
from app.db.session import get_db
from app.email_templates import NEW_USER_TEMPLATE_NAME
from app.routers import security, users
from app.schema.core import User, UserType

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_db.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def start_application():
    app = FastAPI()
    app.include_router(users.router)
    app.include_router(security.router)
    return app


@pytest.fixture(scope="function")
def app() -> Generator[FastAPI, Any, None]:
    print("Creating test database")
    User.metadata.create_all(engine)  # Create the tables.
    _app = start_application()
    yield _app
    User.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def mock_cognito_client():
    with mock_cognitoidp():
        yield


@pytest.fixture(autouse=True)
def mock_ses_client():
    with mock_ses():
        yield


tempPassword = "1234567890Abc!!"


@pytest.fixture(scope="function")
def client(app: FastAPI) -> Generator[TestClient, Any, None]:
    my_config = Config(region_name=app_settings.aws_region)

    cognito_client = boto3.client("cognito-idp", config=my_config)
    ses_client = boto3.client("ses", config=my_config)

    cognito_pool_id = cognito_client.create_user_pool(PoolName="TestUserPool")[
        "UserPool"
    ]["Id"]

    app_settings.cognito_pool_id = cognito_pool_id

    cognito_client_name = "TestAppClient"

    cognito_client_id = cognito_client.create_user_pool_client(
        UserPoolId=cognito_pool_id, ClientName=cognito_client_name
    )["UserPoolClient"]["ClientId"]

    app_settings.cognito_client_id = cognito_client_id
    app_settings.cognito_client_secret = "secret"

    ses_client.verify_email_identity(EmailAddress=app_settings.email_sender_address)

    ses_client.create_template(
        Template={
            "TemplateName": NEW_USER_TEMPLATE_NAME,
            "SubjectPart": "Your email subject",
            "HtmlPart": "<html><body>Your HTML content</body></html>",
            "TextPart": "Your plain text content",
        }
    )

    def generate_test_password():
        print("generate_password")
        return tempPassword

    def _get_test_cognito_client():
        try:
            yield CognitoClient(
                cognito_client,
                ses_client,
                generate_test_password,
            )
        finally:
            pass

    connection = engine.connect()
    session = SessionTesting(bind=connection)

    def _get_test_db():
        try:
            yield session
        finally:
            session.close()

    # Override the clients dependencies with the mock implementations
    app.dependency_overrides[get_cognito_client] = _get_test_cognito_client
    app.dependency_overrides[get_db] = _get_test_db

    with TestClient(app) as client:
        yield client
        connection.close()


data = {"email": "test@example.com", "name": "Test User", "type": UserType.FI.value}


def test_create_user(client):
    response = client.post("/users", json=data)
    assert response.status_code == 200

    response = client.get("/users/1")
    assert response.status_code == 200


def test_duplicate_user(client):
    response = client.post("/users", json=data)
    assert response.status_code == 200
    # duplicate user
    response = client.post("/users", json=data)
    assert response.status_code == 400


def test_login(client):
    responseCreate = client.post("/users", json=data)
    assert responseCreate.status_code == 200

    setupPasswordPayload = {
        "username": data["email"],
        "temp_password": tempPassword,
        "password": tempPassword,
    }
    responseSetupPassword = client.put(
        "/users/change-password", json=setupPasswordPayload
    )
    print(responseSetupPassword.json())
    assert responseSetupPassword.status_code == 200

    loginPayload = {"username": data["email"], "password": tempPassword}
    responseLogin = client.post("/users/login", json=loginPayload)
    print(responseLogin.json())

    assert responseLogin.status_code == 200
    assert responseLogin.json()["access_token"] is not None

    responseAccessProtectedRoute = client.get(
        "/secure-endpoint-example",
        headers={"Authorization": "Bearer " + responseLogin.json()["access_token"]},
    )
    print(responseAccessProtectedRoute.json())

    assert responseAccessProtectedRoute.status_code == 200
    assert (
        responseAccessProtectedRoute.json()["message"] is not None
        and responseAccessProtectedRoute.json()["message"] == "OK"
    )

    responseAccessProtectedRouteWithUser = client.get(
        "/secure-endpoint-example-username-extraction",
        headers={"Authorization": "Bearer " + responseLogin.json()["access_token"]},
    )
    print(responseAccessProtectedRouteWithUser.json())

    assert responseAccessProtectedRouteWithUser.status_code == 200
    print(responseAccessProtectedRouteWithUser.json())
    assert (
        responseAccessProtectedRouteWithUser.json()["username"]
        == setupPasswordPayload["username"]
    )
