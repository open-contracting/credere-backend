from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from app import __main__, models, util
from tests import MockResponse, assert_success, load_json_file

AWARD_ID = "TEST_AWARD_ID"
SUPPLIER_ID = "987654321"

expected_application = load_json_file("fixtures/application_result.json")
award = load_json_file("fixtures/award.json")
expected_award = load_json_file("fixtures/award_result.json")
borrower = load_json_file("fixtures/borrower.json")
# borrower_declined = load_json_file("fixtures/borrower_declined.json")
expected_borrower = load_json_file("fixtures/borrower_result.json")
contract = load_json_file("fixtures/contract.json")
email = load_json_file("fixtures/email.json")

runner = CliRunner()


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
def mock_whole_process(status_code: int, award: dict, borrower: dict, email: dict, function_path: str):
    # Mock all calls to make_request_with_retry from fetch-awards.
    mock = MagicMock(
        side_effect=[
            MockResponse(status_code, award),
            MockResponse(status_code, borrower),
            MockResponse(status_code, email),
            MockResponse(status_code, award),
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


def compare_objects(instance, expected):
    for key, value in instance.model_dump().items():
        match key:
            case (
                "created_at"
                | "updated_at"
                | "secop_data_verification"
                | "_sa_instance_state"
                | "expired_at"
                | "source_data_contracts"
                | "missing_data"
                | "source_data"
            ):
                continue
            case "award_date" | "contractperiod_enddate" | "expired_at" | "source_last_updated_at":
                assert value.strftime("%Y-%m-%dT%H:%M:%S") == expected[key]
            case "size":
                assert value == models.BorrowerSize.NOT_INFORMED
            case "status":
                assert value in (models.BorrowerStatus.ACTIVE, models.ApplicationStatus.PENDING)
            case _:
                assert value == expected[key], f"{instance.__class__.__name__}.{key}"


def test_fetch_previous_borrower_awards_empty(reset_database, sessionmaker, session):
    with (
        mock_response(
            200,
            [],  # changed
            "app.sources.colombia.get_previous_awards",
        ),
        mock_response(
            200,
            award,
            "app.sources.colombia.get_award_by_id_and_supplier",
        ),
        mock_whole_process(
            200,
            contract,
            borrower,
            email,
            "app.sources.make_request_with_retry",
        ),
    ):
        result = runner.invoke(__main__.app, ["fetch-award-by-id-and-supplier", AWARD_ID, SUPPLIER_ID])
        util.get_previous_awards_from_data_source(expected_borrower["id"], sessionmaker)

        assert_success(result)
        assert session.query(models.Award).count() == 1
        assert session.query(models.EventLog).count() == 0, session.query(models.EventLog).one()


def test_fetch_previous_borrower_awards(reset_database, sessionmaker, session):
    # We can make a shallow copy, as we change `id_contrato` only, to make `source_contract_id` different.
    previous_contract = contract[0].copy()
    previous_contract["id_contrato"] = "CO1.test.123456.previous"

    with (
        mock_response(
            200,
            award,  # changed
            "app.sources.colombia.get_previous_awards",
        ),
        mock_response(
            200,
            award,
            "app.sources.colombia.get_award_by_id_and_supplier",
        ),
        patch(
            "app.sources.colombia._get_remote_contract",
            return_value=([previous_contract], "url"),
        ),
        mock_whole_process(
            200,
            [previous_contract],
            borrower,
            email,
            "app.sources.make_request_with_retry",
        ),
    ):
        models.Borrower.create(session, **expected_borrower)
        session.commit()
        util.get_previous_awards_from_data_source(expected_borrower["id"], sessionmaker)

        assert session.query(models.Award).count() == 1
        assert session.query(models.Award).one().previous is True
        assert session.query(models.EventLog).count() == 0, session.query(models.EventLog).one()


def test_fetch_empty_contracts(reset_database):
    with mock_response(200, [], "app.sources.colombia.get_new_awards"):
        result = runner.invoke(__main__.app, ["fetch-awards"])

        assert_success(result, "Fetched 0 contracts\n")


def test_fetch_new_awards_from_date(reset_database, session):
    with (
        mock_response_second_empty(
            200,
            award,
            "app.sources.colombia.get_new_awards",
        ),
        mock_function_response(
            "test_hash_12345678",
            "app.util.get_secret_hash",
        ),
        mock_whole_process(
            200,
            contract,
            borrower,
            email,
            "app.sources.make_request_with_retry",
        ),
    ):
        result = runner.invoke(__main__.app, ["fetch-awards"])
        inserted_award = session.query(models.Award).one()
        inserted_borrower = session.query(models.Borrower).one()
        inserted_application = session.query(models.Application).one()

        assert_success(result, "Fetched 1 contracts\n")
        compare_objects(inserted_award, expected_award)
        compare_objects(inserted_borrower, expected_borrower)
        compare_objects(inserted_application, expected_application)


def test_fetch_award_by_contract_and_supplier_empty(reset_database, session):
    with (
        mock_function_response(
            session,
            "app.db.get_db",
        ),
        mock_response(
            200,
            [],
            "app.sources.colombia.get_award_by_id_and_supplier",
        ),
    ):
        result = runner.invoke(__main__.app, ["fetch-award-by-id-and-supplier", AWARD_ID, SUPPLIER_ID])

        assert_success(result, "No award found with ID TEST_AWARD_ID and supplier ID 987654321\n")


def test_fetch_award_by_id_and_supplier(reset_database, session):
    with (
        mock_function_response(
            session,
            "app.db.get_db",
        ),
        mock_response(
            200,
            award,
            "app.sources.colombia.get_award_by_id_and_supplier",
        ),
        mock_function_response(
            "test_hash_12345678",
            "app.util.get_secret_hash",
        ),
        mock_whole_process(
            200,
            contract,
            borrower,
            email,
            "app.sources.make_request_with_retry",
        ),
    ):
        result = runner.invoke(__main__.app, ["fetch-award-by-id-and-supplier", AWARD_ID, SUPPLIER_ID])
        inserted_award = session.query(models.Award).one()
        inserted_borrower = session.query(models.Borrower).one()
        inserted_application = session.query(models.Application).one()

        assert_success(result)
        compare_objects(inserted_award, expected_award)
        compare_objects(inserted_borrower, expected_borrower)
        compare_objects(inserted_application, expected_application)
