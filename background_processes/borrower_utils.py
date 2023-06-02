import re
from contextlib import contextmanager
from datetime import datetime

import httpx
import sentry_sdk
import background_config
from background_utils import get_secret_hash
from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.schema.core import Borrower

def get_borrower_id(nit_entidad: str):
    with contextmanager(get_db)() as session:
        borrower_id = (
            session.query(Borrower.id)
            .where(Borrower.borrower_identifier == nit_entidad)
            .first()
        )

    if not borrower_id:
        raise HTTPException(status_code=404, detail="No borrower found")
    return borrower_id[0]


def get_borrowers_list():
    with contextmanager(get_db)() as session:
        try:
            borrowers = (
                session.query(Borrower.borrower_identifier)
                .order_by(desc(Borrower.created_at))
                .all()
            )
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=500, detail="Database error occurred"
            ) from e
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
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=500, detail="Database error occurred"
            ) from e

    return obj_db.id


borrowers_list = get_borrowers_list()


def get_or_create_borrower(entry):
    borrower_identifier = get_secret_hash(entry.get("nit_entidad"))
    if borrower_identifier in borrowers_list:
        return get_borrower_id(borrower_identifier)
    borrower_url_email = f"{background_config.BORROWER_EMAIL_URL}?nit={entry['documento_proveedor']}"
    borrower_response_email = httpx.get(borrower_url_email, headers=background_config.headers)
    borrower_response_email_json = borrower_response_email.json()[0]

    if not re.match(background_config.pattern, borrower_response_email_json["correo_entidad"]):
        raise sentry_sdk.capture_exception("Borrower has no valid email address")

    borrower_url = f"{background_config.BORROWER_URL}?nit_entidad={entry['documento_proveedor']}"

    borrower_response = httpx.get(borrower_url, headers=background_config.headers)
    borrower_response_json = borrower_response.json()[0]

    fetched_borrower = {
        "borrower_identifier": borrower_identifier,
        "legal_name": entry.get("nombre_entidad"),
        "email": borrower_response_email_json.get("correo_entidad"),
        "address": "Direccion: {}Ciudad: {}provincia{}estado{}".format(
            borrower_response_json.get("direccion", ""),
            borrower_response_json.get("ciudad", ""),
            borrower_response_json.get("provincia", ""),
            borrower_response_json.get("estado", ""),
        ),
        "legal_identifier": entry.get("nit_entidad"),
        "type": borrower_response_json.get("tipo_organizacion"),
    }

    null_keys = [key for key, value in fetched_borrower.items() if value is None]
    if null_keys:
        error_message = "Null values found for the following keys: {}".format(
            ", ".join(null_keys)
        )
        raise sentry_sdk.capture_exception(error_message)

    borrower_id = insert_borrower(fetched_borrower)
    return borrower_id
