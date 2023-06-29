from contextlib import contextmanager
from datetime import datetime

from app.background_processes.fetcher import fetch_new_awards_from_date
from app.schema import core
from tests.common import common_test_functions

contract = common_test_functions.load_json_file("mock_data/contract.json")
award = common_test_functions.load_json_file("mock_data/award.json")
borrower = common_test_functions.load_json_file("mock_data/borrower.json")

email = common_test_functions.load_json_file("mock_data/email.json")
application_result = common_test_functions.load_json_file(
    "mock_data/application_result.json"
)

award_result = common_test_functions.load_json_file("mock_data/award_result.json")
borrower_result = common_test_functions.load_json_file("mock_data/borrower_result.json")


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
            inserted_award = session.query(core.Award).first()

            inserted_borrower = session.query(core.Borrower).first()
            inserted_application = session.query(core.Application).first()
            print(session.query(core.Application).count())

            try:
                common_test_functions.compare_objects(inserted_award, award_result)
                common_test_functions.compare_objects(
                    inserted_borrower, borrower_result
                )
                common_test_functions.compare_objects(
                    inserted_application, application_result
                )

            finally:
                session.close()
                core.Award.metadata.drop_all(common_test_functions.engine)
