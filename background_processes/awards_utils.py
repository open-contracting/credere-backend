from contextlib import contextmanager
from datetime import datetime, timedelta

import httpx
import sentry_sdk
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.schema.core import Award

from .background_config import URLS, headers


def get_awards_list():
    with contextmanager(get_db)() as session:
        try:
            awards = (
                session.query(Award.source_contract_id)
                .order_by(desc(Award.created_at))
                .all()
            )
        except SQLAlchemyError as e:
            raise e
    return [award[0] for award in awards] or []


def get_last_updated_award_date():
    # depends cannot be used outside of fastapp app call. In order to be able to access session and connect to database
    # we need to create a context manager like this
    with contextmanager(get_db)() as session:
        award = (
            session.query(Award).order_by(desc(Award.source_last_updated_at)).first()
        )
    if not award:
        return None

    return award.source_last_updated_at


def insert_award(award: Award):
    with contextmanager(get_db)() as session:
        try:
            award["created_at"] = datetime.utcnow()
            award["updated_at"] = datetime.utcnow()
            obj_db = Award(**award)
            session.add(obj_db)
            session.commit()
            session.refresh(obj_db)
            return obj_db.id

        except SQLAlchemyError as e:
            raise e


def get_new_contracts(previous=False):
    if previous:
        url = (
            f"{URLS['CONTRACTS']}?$where=es_pyme = 'Si' AND estado_contrato = 'Borrador' "
            f"AND localizaci_n = 'Colombia, Bogotá, Bogotá'"
        )

        return httpx.get(url, headers=headers)

    last_updated_award_date = get_last_updated_award_date()

    if last_updated_award_date:
        one_day = timedelta(days=1)
        converted_date = (last_updated_award_date - one_day).strftime(
            "%Y-%m-%dT00:00:00.000"
        )
        url = (
            f"{URLS['CONTRACTS']}?$where=es_pyme = 'Si' AND estado_contrato = 'Borrador' "
            f"AND ultima_actualizacion >= '{converted_date}' AND localizaci_n = 'Colombia, Bogotá, Bogotá'"
        )
        return httpx.get(url, headers=headers)

    url = (
        f"{URLS['CONTRACTS']}?$where=es_pyme = 'Si' AND estado_contrato = 'Borrador' "
        f"AND localizaci_n = 'Colombia, Bogotá, Bogotá'"
    )
    return httpx.get(url, headers=headers)


def get_or_create_award(entry, borrower_id, previous=False):
    source_contract_id = entry.get("id_contrato", "")
    if source_contract_id in get_awards_list() or not source_contract_id:
        return 0
    else:
        fetched_award = {
            "borrower_id": borrower_id,
            "source_contract_id": source_contract_id,
            "source_url": entry["urlproceso"]["url"],
            "entity_code": entry["codigo_entidad"],
            "procurement_method": entry["modalidad_de_contratacion"],
            "buyer_name": entry["nombre_entidad"],
            "contracting_process_id": entry["proceso_de_compra"],
            "procurement_category": entry["tipo_de_contrato"],
            "previous": previous,
            "payment_method": {
                "habilita_pago_adelantado": entry["habilita_pago_adelantado"],
                "valor_de_pago_adelantado": entry["valor_de_pago_adelantado"],
            },
        }

        award_url = f"{URLS['AWARDS']}?id_del_portafolio={entry['proceso_de_compra']}"

        award_response = httpx.get(award_url, headers=headers)
        award_response_json = award_response.json()[0]

        fetched_award["description"] = award_response_json.get(
            "nombre_del_procedimiento", ""
        )
        fetched_award["award_date"] = award_response_json.get(
            "fecha_adjudicacion", None
        )
        fetched_award["award_amount"] = award_response_json.get(
            "valor_total_adjudicacion", 0
        )
        fetched_award["source_data"] = award_response_json
        fetched_award["source_last_updated_at"] = award_response_json.get(
            "fecha_de_ultima_publicaci)", None
        )
        fetched_award["contract_status"] = award_response_json.get(
            "estado_del_procedimiento", ""
        )
        fetched_award["title"] = award_response_json.get("nombre_del_procedimiento", "")

        if previous:
            fetched_award["contractperiod_startdate"] = entry.get(
                "fecha_de_inicio_del_contrato", None
            )
            fetched_award["contractperiod_enddate"] = entry.get(
                "fecha_de_fin_del_contrato", None
            )

        null_keys = [key for key, value in fetched_award.items() if value is None]
        if null_keys:
            error_message = "Null values found for the following keys: {}".format(
                ", ".join(null_keys)
            )
            sentry_sdk.capture_message(error_message)

        award_id = insert_award(fetched_award)
        return award_id
