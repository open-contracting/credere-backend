import logging
import os
from datetime import datetime, timedelta
from typing import Any, Generator

import boto3
import pytest
from botocore.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from moto import mock_cognitoidp, mock_ses
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.email_templates import templates
from app.core.settings import app_settings
from app.core.user_dependencies import CognitoClient, get_cognito_client
from app.db.session import get_db
from app.routers import applications, lenders, security, users
from app.schema import core
from tests.common.utils import create_enums
from tests.protected_routes import applications_test, lenders_test, users_test

tempPassword = "1234567890Abc!!"


class MockResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self.json_data = json_data

    def json(self):
        return self.json_data


SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", app_settings.test_database_url)
engine = create_engine(SQLALCHEMY_DATABASE_URL)

create_enums(engine)

SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    handlers=[logging.StreamHandler()],  # Output logs to the console
)


def start_application():
    app = FastAPI()
    app.include_router(users.router)
    app.include_router(lenders.router)
    app.include_router(security.router)
    app.include_router(applications.router)
    app.include_router(users_test.router)
    app.include_router(applications_test.router)
    app.include_router(lenders_test.router)
    return app


@pytest.fixture(scope="function")
def app() -> Generator[FastAPI, Any, None]:
    logging.info("Creating test database")
    core.User.metadata.create_all(engine)  # Create the tables.
    _app = start_application()
    yield _app
    core.User.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def mock_cognito_client():
    with mock_cognitoidp():
        yield


@pytest.fixture(autouse=True)
def mock_ses_client():
    with mock_ses():
        yield


def set_application_as_expired():
    connection = engine.connect()
    with SessionTesting(bind=connection) as session:
        db_app = session.query(core.Application).first()
        db_app.expired_at = datetime.now() - timedelta(hours=1)
        session.add(db_app)
        session.commit()


def set_application_status(status: core.ApplicationStatus):
    connection = engine.connect()
    with SessionTesting(bind=connection) as session:
        db_obj = session.query(core.Application).first()
        db_obj.status = status
        session.add(db_obj)
        session.commit()


def set_borrower_status(status: core.BorrowerStatus):
    connection = engine.connect()
    with SessionTesting(bind=connection) as session:
        db_obj = session.query(core.Borrower).first()
        db_obj.status = status
        session.add(db_obj)
        session.commit()


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
            "TemplateName": templates["NEW_USER_TEMPLATE_NAME"],
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
