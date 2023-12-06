import os
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import boto3
import pytest
from botocore.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from moto import mock_cognitoidp, mock_ses
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import aws, dependencies, models
from app.db import get_db
from app.routers import applications, downloads, guest, lenders, statistics, users
from app.settings import app_settings
from tests.protected_routes import users_test  # noqa
from tests.protected_routes import applications_test, borrowers_test  # noqa

tmp_password = "1234567890Abc!!"


class MockResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self.json_data = json_data

    def json(self):
        return self.json_data


SQLALCHEMY_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_test_db() -> Session:
    try:
        db = SessionTesting()
        yield db
    finally:
        if db:
            db.close()


@pytest.fixture(scope="function")
def start_background_db():
    models.User.metadata.create_all(engine)
    yield
    models.User.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def mock_templated_email():
    with patch.object(aws.sesClient, "send_templated_email", MagicMock()) as mock_send_templated_email:
        mock_send_templated_email.return_value = {"MessageId": "123"}
        yield mock_send_templated_email


def start_application():
    app = FastAPI()
    app.include_router(users.router)
    app.include_router(lenders.router)
    app.include_router(applications.router)
    app.include_router(guest.applications.router)
    app.include_router(guest.emails.router)
    app.include_router(downloads.router)
    app.include_router(users_test.router)
    app.include_router(applications_test.router)
    app.include_router(borrowers_test.router)
    app.include_router(statistics.router)
    return app


@pytest.fixture(scope="function")
def app() -> Generator[FastAPI, Any, None]:
    models.User.metadata.create_all(engine)  # Create the tables.
    _app = start_application()
    yield _app
    models.User.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def mock_cognito_client():
    with mock_cognitoidp():
        yield


@pytest.fixture(autouse=True)
def mock_ses_client():
    with mock_ses():
        yield


def create_templates(ses):
    for key in ["-es", ""]:
        ses.create_template(
            Template={
                "TemplateName": f"credere-main{key}",
                "SubjectPart": "Your email subject",
                "HtmlPart": "<html><body>Your HTML content</body></html>",
                "TextPart": "Your plain text content",
            }
        )


@pytest.fixture(scope="function")
def client(app: FastAPI) -> Generator[TestClient, Any, None]:
    my_config = Config(region_name=app_settings.aws_region)

    cognito_client = boto3.client("cognito-idp", config=my_config)
    ses_client = boto3.client("ses", config=my_config)

    cognito_pool_id = cognito_client.create_user_pool(PoolName="TestUserPool")["UserPool"]["Id"]

    app_settings.cognito_pool_id = cognito_pool_id

    cognito_client_name = "TestAppClient"

    cognito_client_id = cognito_client.create_user_pool_client(
        UserPoolId=cognito_pool_id, ClientName=cognito_client_name
    )["UserPoolClient"]["ClientId"]

    app_settings.cognito_client_id = cognito_client_id
    app_settings.cognito_client_secret = "secret"

    ses_client.verify_email_identity(EmailAddress=app_settings.email_sender_address)

    create_templates(ses_client)

    def generate_test_password():
        return tmp_password

    def _get_test_cognito_client():
        try:
            yield aws.CognitoClient(
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
    app.dependency_overrides[dependencies.get_cognito_client] = _get_test_cognito_client
    app.dependency_overrides[get_db] = _get_test_db

    with TestClient(app) as client:
        yield client
        connection.close()
