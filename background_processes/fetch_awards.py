import sys

import sentry_sdk

from .application_utils import create_application
from .awards_utils import get_new_contracts, get_or_create_award
from .background_utils import send_invitation_email
from .borrower_utils import get_or_create_borrower

if __name__ == "__main__":
    previous = False
    if len(sys.argv[1:]):
        previous = True
    contracts_response = get_new_contracts(previous)
    contracts_response_json = contracts_response.json()

    if not contracts_response_json:
        print("No new contracts")
    else:
        for entry in contracts_response_json:
            borrower_id, email = get_or_create_borrower(entry)
            award_id = get_or_create_award(entry, borrower_id, True)
            if award_id and borrower_id:
                try:
                    application_id = create_application(
                        award_id,
                        borrower_id,
                        email,
                        entry.get("nit_entidad"),
                        entry["id_contrato"],
                    )
                    send_invitation_email("URL", email)
                except Exception as e:
                    raise sentry_sdk.capture_exception(
                        "Failed to create application", e
                    )

            else:
                print("Award already exists")
            break
