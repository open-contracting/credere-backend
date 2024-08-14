import os
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import boto3
import moto
import pytest
from botocore.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app import aws, dependencies, models
from app.db import get_db
from app.routers import applications, downloads, guest, lenders, statistics, users
from app.settings import app_settings
from tests import get_test_db
from tests.protected_routes import applications_test, borrowers_test, users_test


@pytest.fixture(autouse=True)
def mock_cognito_client():
    with moto.mock_aws():
        yield


@pytest.fixture(autouse=True)
def mock_ses_client():
    with moto.mock_aws():
        yield


@pytest.fixture(autouse=True)
def mock_templated_email():
    with patch.object(aws.ses_client, "send_templated_email", MagicMock()) as mock:
        mock.return_value = {"MessageId": "123"}
        yield mock


@pytest.fixture(scope="session")
def engine():
    return create_engine(os.getenv("TEST_DATABASE_URL"))


@pytest.fixture
def create_and_drop_database(engine):
    models.SQLModel.metadata.create_all(engine)
    yield
    models.SQLModel.metadata.drop_all(engine)


@pytest.fixture
def app(create_and_drop_database) -> Generator[FastAPI, Any, None]:
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
    yield app


@pytest.fixture
def client(app: FastAPI, engine) -> Generator[TestClient, Any, None]:
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

    for key in ("-es", ""):
        ses_client.create_template(
            Template={
                "TemplateName": f"credere-main{key}",
                "SubjectPart": "Your email subject",
                "HtmlPart": "<html><body>Your HTML content</body></html>",
                "TextPart": "Your plain text content",
            }
        )

    def _get_test_cognito_client():
        try:
            yield aws.CognitoClient(
                cognito_client,
                ses_client,
                lambda: "1234567890Abc!!",
            )
        finally:
            pass

    # Override the clients dependencies with the mock implementations
    app.dependency_overrides[dependencies.get_cognito_client] = _get_test_cognito_client
    app.dependency_overrides[get_db] = get_test_db(engine)

    with TestClient(app) as client:
        yield client
