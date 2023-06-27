import logging
import os
from contextlib import contextmanager
from typing import Any, Generator

import boto3
import pytest
from botocore.config import Config
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from moto import mock_cognitoidp, mock_ses
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.settings import app_settings
from app.core.user_dependencies import CognitoClient, get_cognito_client
from app.db.session import get_db
from app.email_templates import NEW_USER_TEMPLATE_NAME
from app.routers import applications, security, users
from app.schema import core

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_db.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    handlers=[logging.StreamHandler()],  # Output logs to the console
)


def start_application():
    app = FastAPI()
    app.include_router(users.router)
    app.include_router(security.router)
    app.include_router(applications.router)
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


def mock_get_db():
    try:
        db = None
        if SessionTesting:
            core.Application.metadata.create_all(engine)
            db = SessionTesting()

        yield db
    finally:
        if db:
            db.close()


current_dir = os.path.dirname(os.path.abspath(__file__))
filepath = os.path.join(current_dir, "test_files/def.png")

test_application_uuid = "123-456-789"
test_appliation = {
    "uuid": test_application_uuid,
    "primary_email": "proincoingenierias@hotmail.com",
    "status": "PENDING",
    "award_borrower_identifier": "123456789asdqwe",
}
test_award = {
    "source_contract_id": "",
    "title": "",
    "description": "",
    "award_currency": "COP",
    "award_amount": "123456",
}
test_award = {
    "source_contract_id": "",
    "title": "",
    "description": "",
    "award_currency": "COP",
    "award_amount": "123456",
}
test_borrower = {
    "legal_name": "test legal name",
}


data = {"type": "BANK_NAME", "uuid": test_application_uuid}


def test_upload_file(client):
    with contextmanager(mock_get_db)() as session:
        borrower_obj = core.Borrower(**test_borrower)
        session.add(borrower_obj)
        session.commit()
        session.refresh(borrower_obj)

        award_obj = core.Award(**test_award)
        award_obj.borrower_id = borrower_obj.id
        session.add(award_obj)
        session.commit()
        session.refresh(award_obj)

        app_obj = core.Application(**test_appliation)
        app_obj.borrower_id = borrower_obj.id
        app_obj.award_id = award_obj.id
        session.add(app_obj)
        session.commit()
        session.refresh(app_obj)
    with open(filepath, "rb") as file:
        files = {"file": file}
        response = client.post("applications/upload/", data=data, files=files)
        assert response.status_code == status.HTTP_200_OK
