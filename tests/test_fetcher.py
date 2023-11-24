from contextlib import contextmanager

from app import models
from app.commands import fetch_awards
from app.utils import background
from tests.common import common_test_client, common_test_functions

from tests.common.common_test_client import start_background_db  # isort:skip # noqa
from tests.common.common_test_client import mock_templated_email  # isort:skip # noqa
from tests.common.common_test_client import mock_ses_client  # isort:skip # noqa
from tests.common.common_test_client import mock_cognito_client  # isort:skip # noqa
from tests.common.common_test_client import app, client  # isort:skip # noqa


contract = common_test_functions.load_json_file("mock_data/contract.json")
contracts = common_test_functions.load_json_file("mock_data/contracts.json")
award = common_test_functions.load_json_file("mock_data/award.json")
borrower = common_test_functions.load_json_file("mock_data/borrower.json")
borrower_declined = common_test_functions.load_json_file("mock_data/borrower_declined.json")

email = common_test_functions.load_json_file("mock_data/email.json")
application_result = common_test_functions.load_json_file("mock_data/application_result.json")

award_result = common_test_functions.load_json_file("mock_data/award_result.json")
borrower_result = common_test_functions.load_json_file("mock_data/borrower_result.json")


def test_fetch_previous_borrower_awards_empty(start_background_db, caplog):  # noqa
    with caplog.at_level("INFO"):
        with common_test_functions.mock_response(
            200,
            [],
            "app.background_processes.colombia_data_access.get_previous_contracts",
        ):
            background.fetch_previous_awards(models.Borrower(**borrower_result), common_test_client.get_test_db)

    assert "No previous contracts" in caplog.text


def test_fetch_previous_borrower_awards(start_background_db, caplog):  # noqa
    with caplog.at_level("INFO"):
        with common_test_functions.mock_response(
            200,
            contracts,
            "app.background_processes.colombia_data_access.get_previous_contracts",
        ):
            background.fetch_previous_awards(models.Borrower(**borrower_result), common_test_client.get_test_db)

    assert "Previous contracts for" in caplog.text


def test_fetch_empty_contracts(start_background_db, caplog):  # noqa
    with caplog.at_level("INFO"):
        with common_test_functions.mock_response(
            200, [], "app.background_processes.colombia_data_access.get_new_contracts"
        ):
            fetch_awards()

    assert "No new contracts" in caplog.text


def test_fetch_new_awards_borrower_declined(client, mock_templated_email):  # noqa
    client.post("/borrowers-test", json=borrower_declined)

    with common_test_functions.mock_response_second_empty(
        200,
        contract,
        "app.background_processes.colombia_data_access.get_new_contracts",
    ), common_test_functions.mock_whole_process_once(
        200,
        award,
        borrower,
        email,
        "app.background_processes.background_utils.make_request_with_retry",
    ):
        fetch_awards()


def test_fetch_new_awards_from_date(start_background_db, mock_templated_email):  # noqa
    with common_test_functions.mock_response_second_empty(
        200,
        contracts,
        "app.background_processes.colombia_data_access.get_new_contracts",
    ), common_test_functions.mock_function_response(
        "test_hash_12345678",
        "app.util.get_secret_hash",
    ), common_test_functions.mock_whole_process(
        200,
        award,
        borrower,
        email,
        "app.background_processes.background_utils.make_request_with_retry",
    ):
        fetch_awards()

        with contextmanager(common_test_client.get_test_db)() as session:
            inserted_award = session.query(models.Award).first()

            inserted_borrower = session.query(models.Borrower).first()
            inserted_application = session.query(models.Application).first()

            common_test_functions.compare_objects(inserted_award, award_result)
            common_test_functions.compare_objects(inserted_borrower, borrower_result)
            common_test_functions.compare_objects(inserted_application, application_result)
