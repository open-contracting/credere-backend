import json
import os
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.schema import core


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


engine = create_engine("sqlite:///./test_db.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def mock_function_response(content: dict, function_path: str):
    mock = MagicMock(return_value=content)
    with patch(function_path, mock):
        yield mock


@contextmanager
def mock_response(status_code: int, content: dict, function_path: str):
    mock = MagicMock(return_value=MockResponse(status_code, content))
    with patch(function_path, mock):
        yield mock


@contextmanager
def mock_whole_process(
    status_code: int, award: dict, borrower: dict, email: dict, function_path: str
):
    mock = MagicMock(
        side_effect=[
            MockResponse(status_code, award),
            MockResponse(status_code, borrower),
            MockResponse(status_code, email),
        ]
    )

    with patch(function_path, mock):
        yield mock


@contextmanager
def mock_response_second_empty(status_code: int, content: dict, function_path: str):
    mock = MagicMock(
        side_effect=[
            MockResponse(status_code, content),
            MockResponse(200, []),
        ]
    )

    with patch(function_path, mock):
        yield mock


def mock_get_db():
    try:
        db = None
        if SessionLocal:
            core.Award.metadata.create_all(engine)
            db = SessionLocal()

        yield db
    finally:
        if db:
            db.close()
