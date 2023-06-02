from contextlib import contextmanager
from datetime import datetime

import background_config
import httpx
from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.schema.core import Award


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
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=500, detail="Database error occurred"
            ) from e

    return obj_db


def get_new_contracts():
    last_updated_award_date = get_last_updated_award_date()

    if last_updated_award_date:
        converted_date = last_updated_award_date.strftime("%Y-%m-%dT00:00:00.000")
        url = (
            f"{background_config.CONTRACTS_URL}?$where=es_pyme = 'Si' AND estado_contrato = 'Borrador' "
            f"AND ultima_actualizacion >= '{converted_date}' AND localizaci_n = 'Colombia, Bogotá, Bogotá'"
        )

    else:
        url = (
            f"{background_config.CONTRACTS_URL}?$where=es_pyme = 'Si' AND estado_contrato = 'Borrador' "
            f"AND localizaci_n = 'Colombia, Bogotá, Bogotá'"
        )
    return httpx.get(url, headers=background_config.headers)


def create_award(entry, borrower_id, previous=False):
    fetched_award = {
        "borrower_id": borrower_id,
        "source_contract_id": entry["id_contrato"],
        "source_url": entry["urlproceso"]["url"],
        "entity_code": entry["codigo_entidad"],
        "procurement_method": entry["modalidad_de_contratacion"],
        "buyer_name": entry["nombre_entidad"],
        "contracting_process_id": entry["proceso_de_compra"],
        "procurement_category": entry["tipo_de_contrato"],
        "payment_method": {
            "habilita_pago_adelantado": entry["habilita_pago_adelantado"],
            "valor_de_pago_adelantado": entry["valor_de_pago_adelantado"],
        },
    }

    award_url = (
        f"{background_config.AWARDS_URL}?id_del_portafolio={entry['proceso_de_compra']}"
    )

    award_response = httpx.get(award_url, headers=background_config.headers)
    award_response_json = award_response.json()[0]

    fetched_award["description"] = award_response_json["nombre_del_procedimiento"]
    fetched_award["award_date"] = award_response_json.get("fecha_adjudicacion", None)
    fetched_award["award_amount"] = award_response_json["valor_total_adjudicacion"]
    fetched_award["source_data"] = award_response_json
    fetched_award["source_last_updated_at"] = award_response_json[
        "fecha_de_ultima_publicaci"
    ]
    fetched_award["contract_status"] = award_response_json["estado_del_procedimiento"]
    fetched_award["title"] = award_response_json["nombre_del_procedimiento"]

    if previous:
        fetched_award["contractperiod_startdate"] = entry.get(
            "fecha_de_inicio_del_contrato", None
        )
        fetched_award["contractperiod_enddate"] = entry.get(
            "fecha_de_fin_del_contrato", None
        )

    insert_award(fetched_award)
