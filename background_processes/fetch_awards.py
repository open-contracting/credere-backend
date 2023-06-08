import logging
from contextlib import contextmanager

from app.core.user_dependencies import sesClient
from app.db.session import get_db, transaction_session
from app.utils import email_utility

from .application_utils import create_application
from .awards_utils import get_new_contracts, get_or_create_award
from .background_utils import raise_sentry_error
from .borrower_utils import get_or_create_borrower

if __name__ == "__main__":
    index = 0
    contracts_response = get_new_contracts(index)
    contracts_response_json = contracts_response.json()
    if not contracts_response_json:
        logging.info("No new contracts")
    else:
        while len(contracts_response.json()) > 0:
            with contextmanager(get_db)() as session:
                with transaction_session(session):
                    for entry in contracts_response_json:
                        try:
                            borrower_id, email, borrower_name = get_or_create_borrower(
                                entry
                            )
                            award_id, buyer_name, title = get_or_create_award(
                                entry, borrower_id
                            )
                            if award_id == 0:
                                raise_sentry_error(
                                    "Skipping Award - Already Exists on Database", entry
                                )
                            uuid = create_application(
                                award_id,
                                borrower_id,
                                email,
                                entry.get("nit_entidad"),
                                entry["id_contrato"],
                            )
                            email_utility.send_invitation_email(
                                sesClient, uuid, email, borrower_name, buyer_name, title
                            )
                            logging.info("Application created")
                        except ValueError as e:
                            logging.error(
                                "There was an error creating the application.", e
                            )

                    index += 1
                    contracts_response = get_new_contracts(index)
                    contracts_response_json = contracts_response.json()
