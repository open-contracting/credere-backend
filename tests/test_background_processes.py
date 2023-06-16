import logging
import unittest
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import boto3
import pytest
from botocore.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from moto import mock_cognitoidp, mock_ses
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.background_processes import fetcher
from app.core.settings import app_settings
from app.core.user_dependencies import CognitoClient, get_cognito_client
from app.db.session import get_db
from app.email_templates import ACCESS_TO_CREDIT_SCHEME_FOR_MSMES_TEMPLATE_NAME
from app.schema.core import Borrower
from app.utils.email_utility import send_invitation_email

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_db.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def start_application():
    app = FastAPI()
    return app


@pytest.fixture(scope="function")
def app() -> Generator[FastAPI, Any, None]:
    logging.info("Creating test database")
    Borrower.metadata.create_all(engine)  # Create the tables.
    _app = start_application()
    yield _app
    Borrower.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def mock_cognito_client():
    with mock_cognitoidp():
        yield


@pytest.fixture(autouse=True)
def mock_ses_client():
    with mock_ses():
        yield


@pytest.fixture(scope="function")
def client(app: FastAPI) -> Generator[TestClient, Any, None]:
    my_config = Config(region_name=app_settings.aws_region)

    ses_client = boto3.client("ses", config=my_config)

    app_settings.cognito_client_secret = "secret"

    ses_client.verify_email_identity(EmailAddress=app_settings.email_sender_address)

    ses_client.create_template(
        Template={
            "TemplateName": ACCESS_TO_CREDIT_SCHEME_FOR_MSMES_TEMPLATE_NAME,
            "SubjectPart": "Your email subject",
            "HtmlPart": "<html><body>Your HTML content</body></html>",
            "TextPart": "Your plain text content",
        }
    )

    def _get_test_cognito_client():
        try:
            yield CognitoClient(
                ses_client,
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


def test_send_invitation_email():
    ses_client = client

    borrower_name = "John Doe"
    buyer_name = "ABC Company"
    tender_title = "Sample Tender"
    uuid = "abcd-1234"
    email = "test@example.com"

    mock_send_templated_email = MagicMock(
        return_value={"MessageId": "mocked_message_id"}
    )

    ses_client.send_templated_email = mock_send_templated_email

    send_invitation_email(
        ses_client, uuid, email, borrower_name, buyer_name, tender_title
    )

    mock_send_templated_email.assert_called_once()


# mover a json y completar todos los campos
initial_response = {
    "contract1": {
        "nombre_entidad": "One Entity",
        "nit_entidad": "890205176",
        "departamento": "One Department",
        "ciudad": "One City",
    },
    "contract2": {
        "nombre_entidad": "Another Entity",
        "nit_entidad": "123456789",
        "departamento": "Some Department",
        "ciudad": "Some City",
    },
}

modified_response = []

mock_response = MagicMock()
mock_response.status_code = 200
mock_response.json.side_effect = [initial_response, modified_response]

mock_get_new_contracts = MagicMock(return_value=mock_response)


class FetchNewAwardsTestCase(unittest.TestCase):
    def test_fetch_new_awards(self):
        mock_get_new_contracts = MagicMock(return_value=mock_response)

        with patch(
            "app.background_processes.awards_utils.get_new_contracts",
            mock_get_new_contracts,
        ):
            fetcher.fetch_new_awards()


class FetchPreviousAwardsTestCase(unittest.TestCase):
    def test_fetch_previous_awards(self):
        borrower = Borrower(
            legal_identifier="123456789",
            email="test@example.com",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = [initial_response, modified_response]

        mock_get_previous_contracts = MagicMock(return_value=mock_response)

        with patch(
            "app.background_processes.awards_utils.get_previous_contracts",
            mock_get_previous_contracts,
        ):
            fetcher.fetch_previous_awards(borrower)
