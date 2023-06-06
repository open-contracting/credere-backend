from .application_utils import create_application
from .awards_utils import get_new_contracts, get_or_create_award
from .background_utils import send_invitation_email
from .borrower_utils import get_or_create_borrower
from app.db.session import transaction_session
from contextlib import contextmanager
from app.db.session import get_db


if __name__ == "__main__":
    index = 0
    contracts_response = get_new_contracts(index)
    contracts_response_json = contracts_response.json()
    if not contracts_response_json:
        print("No new contracts")
    else:
        while len(contracts_response.json()) > 0:
            with contextmanager(get_db)() as session:
                with transaction_session(session):
                    for entry in contracts_response_json:
                        try:
                            borrower_id, email = get_or_create_borrower(entry)
                            award_id = get_or_create_award(entry, borrower_id)
                            uuid = create_application(
                                award_id,
                                borrower_id,
                                email,
                                entry.get("nit_entidad"),
                                entry["id_contrato"],
                            )
                            send_invitation_email("URL", "testemail@email.com", uuid)
                            print("application created", borrower_id, award_id)
                        except ValueError as e:
                            print("there was an error creating the application.", e)

            index += 1
            contracts_response = get_new_contracts(index)
            contracts_response_json = contracts_response.json()
