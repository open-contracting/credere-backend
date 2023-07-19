import json
import os
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from app.schema import core

datetime_keys = ["award_date", "contractperiod_enddate", "expired_at"]
excluded_keys = [
    "created_at",
    "updated_at",
    "secop_data_verification",
    "_sa_instance_state",
    "expired_at",
    "source_data_contracts",
    "missing_data",
    "source_data",
]


class MockResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self.json_data = json_data

    def json(self):
        return self.json_data


def load_json_file(filename):
    __location__ = os.path.realpath(
        os.path.join(os.getcwd(), os.path.dirname(__file__))
    )
    filepath = os.path.join(__location__, filename)

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
