import re
from datetime import datetime
from typing import Dict

from sqlalchemy.orm.session import Session

from app.schema.core import Borrower, BorrowerStatus

from . import background_utils
from .background_config import URLS, pattern


def get_borrower(borrower_identifier: str, session: Session) -> int:
    obj = (
        session.query(Borrower)
        .filter(Borrower.borrower_identifier == borrower_identifier)
        .first()
    )
    if not obj:
        return None

    if obj.status == BorrowerStatus.DECLINE_OPPORTUNITIES:
        raise ValueError("Borrower choosed to not receive any new opportunity")

    return obj


def insert_borrower(borrower: Borrower, session: Session) -> int:
    obj_db = Borrower(**borrower)
    obj_db.created_at = datetime.utcnow()
    obj_db.missing_data = background_utils.get_missing_data_keys(borrower)

    session.add(obj_db)
    session.flush()

    return obj_db


def update_borrower(
    original_borrower: Borrower, borrower: dict, session: Session
) -> int:
    original_borrower.legal_name = borrower.get("legal_name", "")
    original_borrower.email = borrower.get("email", "")
    original_borrower.address = borrower.get("address", "")
    original_borrower.legal_identifier = borrower.get("legal_identifier", "")
    original_borrower.type = borrower.get("type", "")
    original_borrower.source_data = borrower.get("source_data", "")
    original_borrower.missing_data = background_utils.get_missing_data_keys(borrower)

    session.refresh(original_borrower)
    session.flush()

    return original_borrower


def create_new_borrower(
    borrower_identifier: str, email: str, borrower_entry: dict
) -> Dict[str, str]:
    new_borrower = {
        "borrower_identifier": borrower_identifier,
        "legal_name": borrower_entry.get("nombre_entidad", ""),
        "email": email,
        "address": "Direccion: {}\nCiudad: {}\nProvincia: {}\nEstado: {}".format(
            borrower_entry.get("direccion", "No provisto"),
            borrower_entry.get("ciudad", "No provisto"),
            borrower_entry.get("provincia", "No provisto"),
            borrower_entry.get("estado", "No provisto"),
        ),
        "legal_identifier": borrower_entry.get("nit_entidad", ""),
        "type": borrower_entry.get("tipo_organizacion", ""),
        "source_data": borrower_entry,
    }

    return new_borrower


def get_email(documento_proveedor, entry) -> str:
    borrower_email_url = f"{URLS['BORROWER_EMAIL']}?nit={documento_proveedor}"
    borrower_response_email = background_utils.make_request_with_retry(
        borrower_email_url
    )

    if len(borrower_response_email.json()) == 0:
        error_data = {
            "entry": entry,
            "response": borrower_response_email.json(),
        }
        background_utils.raise_sentry_error(
            "Skipping Award - No email for borrower", error_data
        )

    borrower_response_email_json = borrower_response_email.json()[0]
    email = borrower_response_email_json.get("correo_entidad", "")

    if not re.match(pattern, email):
        error_data = {
            "entry": entry,
            "response": borrower_response_email_json,
        }
        background_utils.raise_sentry_error(
            "Skipping Award - Borrower has no valid email address", error_data
        )

    if len(borrower_response_email.json()) > 1:
        same_email = True
        for borrower_email in borrower_response_email.json():
            if borrower_email.get("correo_entidad", "") != email:
                same_email = False
                break

        if not same_email:
            error_data = {
                "entry": entry,
                "response": borrower_response_email.json(),
            }
            background_utils.raise_sentry_error(
                "Skipping Award - More than one email for borrower", error_data
            )

    return email


def get_or_create_borrower(entry, session: Session) -> Borrower:
    documento_proveedor = entry.get("documento_proveedor", None)
    if not documento_proveedor or documento_proveedor == "No Definido":
        error_data = {"entry": entry}

        background_utils.raise_sentry_error(
            "Skipping Award - documento_proveedor is 'No Definido'",
            error_data,
        )

    borrower_identifier = background_utils.get_secret_hash(documento_proveedor)
    original_borrower = get_borrower(borrower_identifier, session)

    borrower_url = (
        f"{URLS['BORROWER']}&nit_entidad={documento_proveedor}"
        f"&codigo_entidad={entry.get('codigo_proveedor', '')}"
    )
    borrower_response = background_utils.make_request_with_retry(borrower_url)

    if len(borrower_response.json()) > 1:
        error_data = {
            "entry": entry,
            "documento_proveedor": documento_proveedor,
            "response": borrower_response.json(),
        }
        background_utils.raise_sentry_error(
            "Skipping Award - There are more than one borrower for this borrower identifier",
            error_data,
        )

    borrower_response_json = borrower_response.json()[0]

    email = get_email(documento_proveedor, entry)

    new_borrower = create_new_borrower(
        borrower_identifier, email, borrower_response_json
    )

    # existing borrower
    if original_borrower:
        return update_borrower(original_borrower, new_borrower, session)

    return insert_borrower(new_borrower, session)
