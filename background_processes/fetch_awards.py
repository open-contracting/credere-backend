from .application_utils import create_application
from .awards_utils import create_award, get_new_contracts
from .borrower_utils import get_or_create_borrower

if __name__ == "__main__":
    contracts_response = get_new_contracts()
    contracts_response_json = contracts_response.json()

    if not contracts_response_json:
        print("No new contracts")
    else:
        for entry in contracts_response_json:
            borrower_id, email = get_or_create_borrower(entry)
            award_id = create_award(entry, borrower_id)
            if award_id:
                create_application(
                    borrower_id,
                    award_id,
                    email,
                    entry.get("nit_entidad"),
                    entry["id_contrato"],
                )
            else:
                print("Award already exists")
