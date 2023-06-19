import pytest
from sqlalchemy.orm import sessionmaker
from app.schema.core import Award, Borrower
from app.background_processes import awards_utils
from app.background_processes.borrower_utils import get_or_create_borrower
from sqlmodel import create_engine
from unittest.mock import MagicMock, patch
import os
import json


class MockResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self.json_data = json_data

    def json(self):
        return self.json_data


def load_json_file(filename):
    # Get the directory path of the current file
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Construct the full path to the JSON file
    filepath = os.path.join(current_dir, filename)

    # Open the JSON file and read its contents
    with open(filepath, "r") as json_file:
        data = json.load(json_file)

    return data


# Load the contract data
contract = load_json_file("contract.json")

# Load the award data
award = load_json_file("award.json")

# Load the borrower data
borrower = load_json_file("borrower.json")


@pytest.fixture(scope="function")
def db_session():
    # Create a database session
    SQLALCHEMY_DATABASE_URL = "sqlite:///./test_db.db"
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionTesting()

    # Create tables
    Award.metadata.create_all(engine)

    # Yield the session to the test case
    yield session

    # Drop tables and close the session
    session.close()
    Award.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def mock_get_email():
    # Create a mock for make_request_with_retry
    mock = MagicMock(return_value=MockResponse(200, "test_email@test.com"))

    # Patch the make_request_with_retry function
    with patch(
        "app.background_processes.colombia_data_access.get_email",
        mock,
    ):
        yield mock


@pytest.fixture(scope="function")
def mock_request_award():
    # Create a mock for make_request_with_retry
    mock = MagicMock(return_value=MockResponse(200, award))

    # Patch the make_request_with_retry function
    with patch(
        "app.background_processes.background_utils.make_request_with_retry",
        mock,
    ):
        yield mock


@pytest.fixture(scope="function")
def mock_request_borrower():
    # Create a mock for make_request_with_retry
    mock = MagicMock(return_value=MockResponse(200, borrower))

    # Patch the make_request_with_retry function
    with patch(
        "app.background_processes.background_utils.make_request_with_retry",
        mock,
    ):
        yield mock


@pytest.fixture(scope="function")
def mock_empty_request():
    # Create a mock for make_request_with_retry
    mock = MagicMock(return_value=MockResponse(200, []))

    # Patch the make_request_with_retry function
    with patch(
        "app.background_processes.background_utils.make_request_with_retry",
        mock,
    ):
        yield mock


def test_create_award(db_session, mock_request_award):
    # Call the function under test
    result = awards_utils.create_award(contract, db_session)
    inserted_award = db_session.query(Award).first()

    # Assert the result
    assert result == inserted_award


def test_create_duplicate_award(db_session, mock_request_award):
    with pytest.raises(ValueError) as cm:
        awards_utils.create_award(contract, db_session)
        awards_utils.create_award(contract, db_session)

    # Assert the error message
    assert (
        str(cm.value) == "Skipping Award [previous False] - Already exists on database"
    )


def test_create_award_empty_response(db_session, mock_empty_request):
    with pytest.raises(ValueError) as cm:
        awards_utils.create_award(contract, db_session)

    # Assert the error message
    assert (
        str(cm.value) == "Skipping Award [previous False]"
        " - Zero or more than one results for 'proceso_de_compra' and 'proveedor_adjudicado'",
    )


def test_create_award_no_source_contract_id(db_session, mock_request_award):
    # remove id_contrato so it raises an error
    contract.pop("id_contrato")
    with pytest.raises(ValueError) as cm:
        awards_utils.create_award(contract, db_session)

    # Assert the error message
    assert (str(cm.value) == "ValueError: Skipping Award - No id_contrato",)


def test_create_borrower(db_session, mock_request_borrower, mock_get_email):
    result = get_or_create_borrower(contract, db_session)
    inserted_borrower = db_session.query(Borrower).first()
    assert result == inserted_borrower
