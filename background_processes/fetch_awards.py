from awards_utils import create_award, get_new_contracts
from borrower_utils import get_or_create_borrower

contracts_response = get_new_contracts()
contracts_response_json = contracts_response.json()

if not contracts_response_json:
    print("No new contracts")
else:
    for entry in contracts_response_json:
        borrower_id = get_or_create_borrower(entry)
        fetched_award = create_award(entry, borrower_id)
        break
