import re
from contextlib import contextmanager
from datetime import datetime

import httpx
import sentry_sdk
from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.schema.core import Borrower

from .background_config import URLS, headers, pattern
from .background_utils import get_secret_hash


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
            raise HTTPException(
                status_code=500, detail="Database error occurred"
            ) from e


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
            return obj_db.id
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=500, detail="Database error occurred"
            ) from e


def get_or_create_borrower(entry) -> tuple[int, str]:
    borrowers_list = get_borrowers_list()
    borrower_identifier = get_secret_hash(entry.get("nit_entidad"))
    if borrower_identifier in borrowers_list:
        borrower_id, email = get_borrower_id_and_email(borrower_identifier)
    else:
        borrower_url_email = (
            f"{URLS['BORROWER_EMAIL']}?nit={entry['documento_proveedor']}"
        )
        borrower_response_email = httpx.get(borrower_url_email, headers=headers)
        borrower_response_email_json = borrower_response_email.json()[0]

        if not re.match(pattern, borrower_response_email_json["correo_entidad"]):
            raise sentry_sdk.capture_exception("Borrower has no valid email address")

        borrower_url = f"{URLS['BORROWER']}?nit_entidad={entry['documento_proveedor']}"

        borrower_response = httpx.get(borrower_url, headers=headers)
        borrower_response_json = borrower_response.json()[0]

        legal_identifier = entry.get("nit_entidad")
        email = borrower_response_email_json.get("correo_entidad")
        fetched_borrower = {
            "borrower_identifier": borrower_identifier,
            "legal_name": entry.get("nombre_entidad"),
            "email": email,
            "address": "Direccion: {}Ciudad: {}provincia{}estado{}".format(
                borrower_response_json.get("direccion", ""),
                borrower_response_json.get("ciudad", ""),
                borrower_response_json.get("provincia", ""),
                borrower_response_json.get("estado", ""),
            ),
            "legal_identifier": legal_identifier,
            "type": borrower_response_json.get("tipo_organizacion"),
        }

        null_keys = [key for key, value in fetched_borrower.items() if value is None]
        if null_keys:
            error_message = "Null values found for the following keys: {}".format(
                ", ".join(null_keys)
            )
            sentry_sdk.capture_exception(error_message)

        borrower_id = insert_borrower(fetched_borrower)

    return borrower_id, email
