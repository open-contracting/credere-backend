import logging
from typing import Any, Generator
import boto3
import pytest
from botocore.config import Config
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from moto import mock_cognitoidp, mock_ses
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.email_templates import NEW_USER_TEMPLATE_NAME

from app.core.settings import app_settings
from app.core.user_dependencies import CognitoClient, get_cognito_client
from app.db.session import get_db
from app.routers import security, users, lenders
from app.schema.core import User, UserType

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_db.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_test_db() -> Generator:
    try:
        db = None
        if SessionTesting:
            User.metadata.create_all(engine)
            db = SessionTesting()

        yield db
    finally:
        if db:
            db.close()


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    handlers=[logging.StreamHandler()],  # Output logs to the console
)


def start_application():
    app = FastAPI()
    app.include_router(users.router)
    app.include_router(security.router)
    app.include_router(lenders.router)
    return app


@pytest.fixture(scope="function")
def app() -> Generator[FastAPI, Any, None]:
    logging.info("Creating test database")
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
        logging.info("generate_password")
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

OCP_user = {
    "email": "OCP@example.com",
    "name": "Test User",
    "external_id": "123-456-789",
    "type": UserType.OCP.value,
}

FI_user = {
    "email": "FI_user@example.com",
    "name": "Test User",
    "external_id": "123-456-789",
    "type": UserType.FI.value,
}


def create_test_user(client, user_data):
    responseCreate = client.post("/users", json=user_data)
    assert responseCreate.status_code == status.HTTP_200_OK

    setupPasswordPayload = {
        "username": user_data["email"],
        "temp_password": tempPassword,
        "password": tempPassword,
    }
    client.put("/users/change-password", json=setupPasswordPayload)

    loginPayload = {"username": user_data["email"], "password": tempPassword}
    responseLogin = client.post("/users/login", json=loginPayload)

    return {"Authorization": "Bearer " + responseLogin.json()["access_token"]}


def test_lender(client):
    OCP_headers = create_test_user(client, OCP_user)
    FI_headers = create_test_user(client, FI_user)
    response = client.post("/lenders/", json=lender, headers=OCP_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/lenders/", headers=OCP_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/lenders/1", headers=OCP_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.put("/lenders/1", json=lender_modified, headers=OCP_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.put("/lenders/1", json=lender_modified, headers=OCP_headers)
    assert response.json()["name"] == lender_modified["name"]
    assert response.status_code == status.HTTP_200_OK

    response = client.post("/lenders/", json=lender, headers=FI_headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
