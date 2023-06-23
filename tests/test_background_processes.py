from contextlib import contextmanager
from datetime import datetime

from sqlalchemy.orm import defer

from app.background_processes.fetcher import fetch_new_awards_from_date
from app.schema import core
from tests.common import common_test_functions

# Load the contract data
contract = common_test_functions.load_json_file("mock_data/contract.json")

# Load the award data
award = common_test_functions.load_json_file("mock_data/award.json")
award_result = common_test_functions.load_json_file("mock_data/award_result.json")

# Load the borrower data
borrower = common_test_functions.load_json_file("mock_data/borrower.json")
borrower_result = common_test_functions.load_json_file("mock_data/borrower_result.json")

email = common_test_functions.load_json_file("mock_data/email.json")
application_result = common_test_functions.load_json_file(
    "mock_data/application_result.json"
)


award_excluded_keys = [
    "award_amount",
    "contractperiod_enddate",
    "source_data_contracts",
    "created_at",
    "updated_at",
]

borrower_excluded_keys = [
    "created_at",
    "updated_at",
]

application_excluded_keys = ["amount_requested", "contract_amount_submitted"]


def test_fetch_new_awards_from_date():
    date = "2022-06-20T00:00:00.000"
    last_updated_award_date = datetime.fromisoformat(date)

    with common_test_functions.mock_response_second_empty(
        200,
        contract,
        "app.background_processes.awards_utils.get_new_contracts",
    ), common_test_functions.mock_function_response(
        None,
        "app.background_processes.awards_utils.get_existing_award",
    ), common_test_functions.mock_function_response(
        "test_hash_12345678",
        "app.background_processes.background_utils.get_secret_hash",
    ), common_test_functions.mock_function_response(
        1,
        "app.utils.email_utility.send_invitation_email",
    ), common_test_functions.mock_function_response(
        None,
        "app.background_processes.application_utils.get_existing_application",
    ), common_test_functions.mock_whole_process(
        200,
        award,
        borrower,
        email,
        "app.background_processes.background_utils.make_request_with_retry",
    ):
        fetch_new_awards_from_date(
            last_updated_award_date,
            "email_invitation",
            common_test_functions.mock_get_db,
        )

        with contextmanager(common_test_functions.mock_get_db)() as session:
            inserted_award = (
                session.query(core.Award)
                .options(*[defer(field) for field in award_excluded_keys])
                .first()
            )

            inserted_borrower = (
                session.query(core.Borrower)
                .options(*[defer(field) for field in borrower_excluded_keys])
                .first()
            )
            inserted_application = (
                session.query(core.Application)
                .options(*[defer(field) for field in application_excluded_keys])
                .first()
            )

            try:
                for key, value in inserted_award.__dict__.items():
                    if key == "award_date":
                        formatted_dt = value.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
                        assert formatted_dt == award_result[key]
                        return
                    if key != "_sa_instance_state":
                        assert award_result[key] == value

                for key, value in inserted_borrower.__dict__.items():
                    if key == "size":
                        assert core.BorrowerSize.NOT_INFORMED == value
                        return
                    if key != "_sa_instance_state":
                        assert borrower_result[key] == value
                for key, value in inserted_application.__dict__.items():
                    if key != "_sa_instance_state":
                        assert application_result[key] == value
            finally:
                core.Award.metadata.drop_all(common_test_functions.engine)
