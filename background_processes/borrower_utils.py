import re
from contextlib import contextmanager
from datetime import datetime

import httpx

from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.schema.core import Borrower

from .background_config import URLS, headers, pattern
from .background_utils import get_secret_hash, raise_sentry_error


def get_borrower_id_and_email(nit_entidad: str):
    with contextmanager(get_db)() as session:
        try:
            obj = (
                session.query(Borrower)
                .where(Borrower.borrower_identifier == nit_entidad)
                .first()
            )
            if not obj:
                raise HTTPException(status_code=404, detail="No borrower found")
            return obj.id, obj.email
        except SQLAlchemyError as e:
            raise e


def get_borrowers_list():
    with contextmanager(get_db)() as session:
        try:
            borrowers = (
                session.query(Borrower.borrower_identifier)
                .order_by(desc(Borrower.created_at))
                .all()
            )
        except SQLAlchemyError as e:
            raise e
    return [borrower[0] for borrower in borrowers] or []


def insert_borrower(borrower: Borrower):
    with contextmanager(get_db)() as session:
        try:
            borrower["created_at"] = datetime.utcnow()
            borrower["updated_at"] = datetime.utcnow()
            obj_db = Borrower(**borrower)
            session.add(obj_db)
            session.commit()
            session.refresh(obj_db)
            return obj_db.id
        except SQLAlchemyError as e:
            raise e


def create_new_borrower(
    borrower_identifier: str, email: str, borrower_entry: dict
) -> dict:
    new_borrower = {
        "borrower_identifier": borrower_identifier,
        "legal_name": borrower_entry.get("nombre_entidad", ""),
        "email": email,
        "address": "Direccion: {}Ciudad: {}provincia{}estado{}".format(
            borrower_entry.get("direccion", ""),
            borrower_entry.get("ciudad", ""),
            borrower_entry.get("provincia", ""),
            borrower_entry.get("estado", ""),
        ),
        "legal_identifier": borrower_entry.get("nit_entidad", ""),
        "type": borrower_entry.get("tipo_organizacion", ""),
    }
    return new_borrower


def get_email(borrower_email, entry) -> str:
    borrower_response_email = httpx.get(borrower_email, headers=headers)

    if borrower_response_email.json() != 1:
        error_data = {
            "entry": entry,
            "response": borrower_response_email.json(),
        }
        raise_sentry_error("Email endpoint returned an invalidad response", error_data)

    borrower_response_email_json = borrower_response_email.json()[0]
    email = borrower_response_email_json.get("correo_entidad", "")
    if not re.match(pattern, email):
        error_data = {
            "entry": entry,
            "response": borrower_response_email_json,
        }
        raise_sentry_error("Borrower has no valid email address", error_data)
    return email


def get_or_create_borrower(entry):
    borrowers_list = get_borrowers_list()
    borrower_identifier = get_secret_hash(entry.get("documento_proveedor", ""))

    # checks if hashed nit exist in our table
    if borrower_identifier in borrowers_list:
        borrower_id, email = get_borrower_id_and_email(borrower_identifier)
    else:
        borrower_url = f"{URLS['BORROWER']}&nit_entidad={entry['documento_proveedor']}"
        borrower_response = httpx.get(borrower_url, headers=headers)

        if len(borrower_response.json()) > 1:
            error_data = {"entry": entry, "response": borrower_response.json()}
            raise_sentry_error(
                "There are more than one borrowers in this borrower identifier entry",
                error_data,
            )

        borrower_response_json = borrower_response.json()[0]

        borrower_email = f"{URLS['BORROWER_EMAIL']}?nit={entry['documento_proveedor']}"

        email = get_email(borrower_email, entry)

        new_borrower = create_new_borrower(
            borrower_identifier, email, borrower_response_json
        )

        borrower_id = insert_borrower(new_borrower)

    return borrower_id, email
