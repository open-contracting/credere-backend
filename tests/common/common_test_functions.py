import json
import os
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from sqlalchemy import Enum, create_engine
from sqlalchemy.orm import sessionmaker

from app.core.settings import app_settings
from app.schema import core

datetime_keys = ["award_date", "contractperiod_enddate", "expired_at"]
excluded_keys = [
    "created_at",
    "updated_at",
    "secop_data_verification",
    "_sa_instance_state",
    "expired_at",
]


class MockResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self.json_data = json_data

    def json(self):
        return self.json_data


def load_json_file(filename):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(current_dir, filename)

    with open(filepath, "r") as json_file:
        data = json.load(json_file)

    return data


application_status_values = (
    "PENDING",
    "ACCEPTED",
    "LAPSED",
    "DECLINED",
    "SUBMITTED",
    "STARTED",
    "APPROVED",
    "CONTRACT_UPLOADED",
    "COMPLETED",
    "REJECTED",
    "INFORMATION_REQUESTED",
)

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", app_settings.test_database_url)
engine = create_engine(SQLALCHEMY_DATABASE_URL)
existing_enum_types = engine.execute(
    "SELECT typname FROM pg_type WHERE typtype = 'e'"
).fetchall()
enum_exists = ("application_status",) in existing_enum_types
ApplicationStatusEnum = Enum(
    *application_status_values, name="application_status", create_type=False
)

if not enum_exists:
    engine.execute(
        "CREATE TYPE application_status AS ENUM %s" % str(application_status_values)
    )


SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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


def compare_objects(
    fetched_model,
    expected_result,
):
    for key, value in fetched_model.__dict__.items():
        if key in excluded_keys:
            continue

        if key in datetime_keys:
            formatted_dt = value.strftime("%Y-%m-%dT%H:%M:%S")
            assert formatted_dt == expected_result[key]
            continue

        if key == "size":
            assert core.BorrowerSize.NOT_INFORMED == value
            continue
        if key == "status":
            assert (
                core.BorrowerStatus.ACTIVE == value
                or core.ApplicationStatus.PENDING == value
            )
            continue

        assert expected_result[key] == value


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


def mock_get_db_with_drop():
    try:
        db = None
        if SessionTesting:
            core.Application.metadata.create_all(engine)
            db = SessionTesting()

        yield db
    finally:
        if db:
            db.close()
            core.Application.metadata.drop_all(engine)
