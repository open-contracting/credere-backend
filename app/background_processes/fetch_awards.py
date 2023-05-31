from fetch_utilities import complete_award, complete_borrower, get_new_contracts

contracts_response = get_new_contracts()
contracts_response_json = contracts_response.json()

for entry in contracts_response_json:
    borrower_id = complete_borrower(entry)
    fetched_award = complete_award(entry, borrower_id)
