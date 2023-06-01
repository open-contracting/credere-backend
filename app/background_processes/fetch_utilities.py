import base64
import hashlib
import hmac
import os
import re
from contextlib import contextmanager

import httpx
import sentry_sdk
from dotenv import dotenv_values
from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.schema.core import Award, Borrower

CONTRACTS_URL = "https://www.datos.gov.co/resource/jbjy-vk9h.json"
AWARDS_URL = "https://www.datos.gov.co/resource/p6dx-8zbt.json"
BORROWER_EMAIL_URL = "https://www.datos.gov.co/resource/vzyx-b5wf.json"
BORROWER_URL = "https://www.datos.gov.co/resource/4ex9-j3n8.json"

pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"

config_env = {
    **dotenv_values(".env"),
    **os.environ,
}  # config are loading separately from main app in order to avoid package dependencies

secop_app_token: str = config_env.get("SECOP_APP_TOKEN", None)
hash_key: str = config_env.get("HASH_KEY", None)
headers = {"X-App-Token": secop_app_token}


def get_secret_hash(nit_entidad: str):
    key = hash_key
    message = bytes(nit_entidad, "utf-8")
    key = bytes(key, "utf-8")
    return base64.b64encode(
        hmac.new(key, message, digestmod=hashlib.sha256).digest()
    ).decode()


def get_last_award_creation_date():
    # depends cannot be used outside of fastapp app call. In order to be able to access session and connect to database
    # we need to create a context manager like this
    with contextmanager(get_db)() as session:
        award = session.query(Award).order_by(desc(Award.created_at)).first()
    if not award:
        return None
    return award.created_at


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

    if not borrowers:
        raise HTTPException(status_code=404, detail="No borrowers found")

    return [borrower[0] for borrower in borrowers]


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


def insert_borrower(borrower: Borrower):
    with contextmanager(get_db)() as session:
        try:
            obj_db = Borrower(**borrower)
            session.add(obj_db)
            session.commit()
            session.refresh(obj_db)
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=500, detail="Database error occurred"
            ) from e

    return obj_db.id


def insert_award(award: Award):
    with contextmanager(get_db)() as session:
        try:
            obj_db = Award(**award)
            session.add(obj_db)
            session.commit()
            session.refresh(obj_db)
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=500, detail="Database error occurred"
            ) from e

    return obj_db


get_last_award_creation_date()
borrowers_list = get_borrowers_list()


def get_new_contracts():
    last_award_creation_date = get_last_award_creation_date()

    if not last_award_creation_date:
        converted_date = last_award_creation_date.strftime("%Y-%m-%dT00:00:00.000")
        url = (
            f"{CONTRACTS_URL}?$where=es_pyme = 'Si' AND estado_contrato = 'Borrador' "
            f"AND ultima_actualizacion >= '{converted_date}' AND localizaci_n = 'Colombia, Bogotá, Bogotá'"
        )

    else:
        url = (
            f"{CONTRACTS_URL}?$where=es_pyme = 'Si' AND estado_contrato = 'Borrador' "
            f"AND localizaci_n = 'Colombia, Bogotá, Bogotá'"
        )
    return httpx.get(url, headers=headers)


def get_or_create_borrower(entry):
    if entry["nit_entidad"] in borrowers_list:
        return get_borrower_id(entry["nit_entidad"])
    borrower_url_email = f"{BORROWER_EMAIL_URL}?nit={entry['documento_proveedor']}"
    borrower_response_email = httpx.get(borrower_url_email, headers=headers)
    borrower_response_email_json = borrower_response_email.json()[0]

    if not re.match(pattern, borrower_response_email_json["correo_entidad"]):
        return None

    borrower_url = f"{BORROWER_URL}?nit_entidad={entry['documento_proveedor']}"

    borrower_response = httpx.get(borrower_url, headers=headers)
    borrower_response_json = borrower_response.json()[0]

    fetched_borrower = {
        "borrower_identifier": get_secret_hash(entry.get("nit_entidad")),
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


def create_award(entry, borrower_id):
    fetched_award = {
        "contracting_process_id": entry["proceso_de_compra"],
        "award_currency": "Colombian Peso",
        "buyer_name": entry["nombre_entidad"],
        "source_url": entry["urlproceso"]["url"],
        "entity_code": entry["codigo_entidad"],
        "previous": False,
        "procurement_method": entry["modalidad_de_contratacion"],
        "procurement_category": entry["tipo_de_contrato"],
        "source_data": entry["urlproceso"],
        "payment_method": {
            "habilita_pago_adelantado": entry["habilita_pago_adelantado"],
            "valor_de_pago_adelantado": entry["valor_de_pago_adelantado"],
        },
        "award_amount": None,
        "title": None,
        "description": None,
        "award_date": None,
        "contractperiod_startdate": None,
        "contractperiod_enddate": None,
        "contract_status": None,
        "source_last_updated_at": None,
        "borrower_id": borrower_id,
    }

    award_url = f"{AWARDS_URL}?id_del_portafolio={entry['proceso_de_compra']}"

    award_response = httpx.get(award_url, headers=headers)
    award_response_json = award_response.json()[0]

    fetched_award["award_amount"] = award_response_json["valor_total_adjudicacion"]
    fetched_award["title"] = award_response_json["nombre_del_procedimiento"]
    fetched_award["description"] = award_response_json["nombre_del_procedimiento"]
    fetched_award["award_date"] = award_response_json.get("fecha_adjudicacion", None)
    fetched_award["contractperiod_startdate"] = entry.get(
        "fecha_de_inicio_del_contrato", None
    )
    fetched_award["contractperiod_enddate"] = entry.get(
        "fecha_de_fin_del_contrato", None
    )

    fetched_award["contract_status"] = award_response_json["estado_del_procedimiento"]
    fetched_award["source_last_updated_at"] = award_response_json[
        "fecha_de_ultima_publicaci"
    ]
    fetched_award["borrower_id"] = borrower_id
    insert_award(fetched_award)
