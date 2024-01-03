import json
import os
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from app import models
from app.commands import fetch_awards
from app.utils import background
from tests import MockResponse, get_test_db


def _load_json_file(filename):
    __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
    filepath = os.path.join(__location__, filename)

    with open(filepath, "r") as json_file:
        data = json.load(json_file)

    return data


contract = _load_json_file("mock_data/contract.json")
contracts = _load_json_file("mock_data/contracts.json")
award = _load_json_file("mock_data/award.json")
borrower = _load_json_file("mock_data/borrower.json")
borrower_declined = _load_json_file("mock_data/borrower_declined.json")

email = _load_json_file("mock_data/email.json")
application_result = _load_json_file("mock_data/application_result.json")

award_result = _load_json_file("mock_data/award_result.json")
borrower_result = _load_json_file("mock_data/borrower_result.json")


@contextmanager
def _mock_function_response(content: dict, function_path: str):
    mock = MagicMock(return_value=content)
    with patch(function_path, mock):
        yield mock


@contextmanager
def _mock_response(status_code: int, content: dict, function_path: str):
    mock = MagicMock(return_value=MockResponse(status_code, content))
    with patch(function_path, mock):
        yield mock


@contextmanager
def _mock_whole_process_once(status_code: int, award: dict, borrower: dict, email: dict, function_path: str):
    # this will mock the whole process of the fetcher once responding to make_request_with_retry in order
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
def _mock_whole_process(status_code: int, award_mock: dict, borrower_mock: dict, email_mock: dict, function_path: str):
    # this will mock the whole process of the fetcher responding to make_request_with_retry in order
    #
    mock = MagicMock(
        side_effect=[
            MockResponse(status_code, award_mock),
            MockResponse(status_code, borrower_mock),
            MockResponse(status_code, email_mock),
        ]
    )

    with patch(function_path, mock):
        yield mock


@contextmanager
def _mock_response_second_empty(status_code: int, content: dict, function_path: str):
    mock = MagicMock(
        side_effect=[
            MockResponse(status_code, content),
            MockResponse(200, []),
        ]
    )

    with patch(function_path, mock):
        yield mock


def _compare_objects(
    fetched_model,
    expected_result,
):
    for key, value in fetched_model.__dict__.items():
        if key in {
            "created_at",
            "updated_at",
            "secop_data_verification",
            "_sa_instance_state",
            "expired_at",
            "source_data_contracts",
            "missing_data",
            "source_data",
        }:
            continue

        if key in {"award_date", "contractperiod_enddate", "expired_at"}:
            formatted_dt = value.strftime("%Y-%m-%dT%H:%M:%S")
            assert formatted_dt == expected_result[key]
            continue

        if key == "size":
            assert models.BorrowerSize.NOT_INFORMED == value
            continue
        if key == "status":
            assert models.BorrowerStatus.ACTIVE == value or models.ApplicationStatus.PENDING == value
            continue

        assert expected_result[key] == value


def test_fetch_previous_borrower_awards_empty(engine, create_and_drop_database, caplog):
    with caplog.at_level("INFO"):
        with _mock_response(
            200,
            [],
            "app.sources.colombia.get_previous_contracts",
        ):
            background.fetch_previous_awards(models.Borrower(**borrower_result), get_test_db(engine))

    assert "No previous contracts" in caplog.text


def test_fetch_previous_borrower_awards(engine, create_and_drop_database, caplog):
    with caplog.at_level("INFO"):
        with _mock_response(
            200,
            contracts,
            "app.sources.colombia.get_previous_contracts",
        ):
            background.fetch_previous_awards(models.Borrower(**borrower_result), get_test_db(engine))

    assert "Previous contracts for" in caplog.text


def test_fetch_empty_contracts(create_and_drop_database, caplog):
    with caplog.at_level("INFO"):
        with _mock_response(200, [], "app.sources.colombia.get_new_contracts"):
            fetch_awards()

    assert "No new contracts" in caplog.text


def test_fetch_new_awards_from_date(engine, create_and_drop_database):
    with _mock_response_second_empty(
        200,
        contracts,
        "app.sources.colombia.get_new_contracts",
    ), _mock_function_response(
        "test_hash_12345678",
        "app.util.get_secret_hash",
    ), _mock_whole_process(
        200,
        award,
        borrower,
        email,
        "app.sources.make_request_with_retry",
    ):
        fetch_awards()

        with contextmanager(get_test_db(engine))() as session:
            inserted_award = session.query(models.Award).one()
            inserted_borrower = session.query(models.Borrower).one()
            inserted_application = session.query(models.Application).one()
            _compare_objects(inserted_award, award_result)
            _compare_objects(inserted_borrower, borrower_result)
            _compare_objects(inserted_application, application_result)


def test_fetch_award_by_contract_and_supplier_empty(engine, create_and_drop_database, caplog):
    contract_id = "CO1.test.123456"
    supplier_id = "987654321"
    with caplog.at_level("INFO"):
        with _mock_response(
            200,
            [],
            "app.sources.colombia.get_contract_by_contract_and_supplier",
        ):
            background.fetch_award_by_contract_and_supplier(contract_id, supplier_id, get_test_db(engine))

    assert f"The contract with id {contract_id} and supplier id {supplier_id} was not found" in caplog.text


def test_fetch_award_by_contract_and_supplier(engine, create_and_drop_database):
    contract_id = "CO1.test.123456"
    supplier_id = "987654321"
    with _mock_response(
        200,
        contract,
        "app.sources.colombia.get_contract_by_contract_and_supplier",
    ), _mock_function_response(
        "test_hash_12345678",
        "app.util.get_secret_hash",
    ), _mock_whole_process(
        200,
        award,
        borrower,
        email,
        "app.sources.make_request_with_retry",
    ):
        background.fetch_award_by_contract_and_supplier(contract_id, supplier_id, get_test_db(engine))

        with contextmanager(get_test_db(engine))() as session:
            inserted_award = session.query(models.Award).one()
            inserted_borrower = session.query(models.Borrower).one()
            inserted_application = session.query(models.Application).one()
            _compare_objects(inserted_award, award_result)
            _compare_objects(inserted_borrower, borrower_result)
            _compare_objects(inserted_application, application_result)
