from contextlib import contextmanager
from datetime import datetime, timedelta

import httpx
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import app_settings, get_db
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


def create_new_award(borrower_id: int, source_contract_id: str, entry: dict) -> dict:
    return {
        "borrower_id": borrower_id,
        "source_contract_id": source_contract_id,
        "source_url": entry["urlproceso"]["url"],
        "entity_code": entry["codigo_entidad"],
        "procurement_method": entry["modalidad_de_contratacion"],
        "buyer_name": entry["nombre_entidad"],
        "contracting_process_id": entry["proceso_de_compra"],
        "procurement_category": entry["tipo_de_contrato"],
        "previous": False,
        "payment_method": {
            "habilita_pago_adelantado": entry["habilita_pago_adelantado"],
            "valor_de_pago_adelantado": entry["valor_de_pago_adelantado"],
        },
    }


def get_new_contracts(index: int):
    last_updated_award_date = get_last_updated_award_date()

    if last_updated_award_date:
        one_day = timedelta(days=1)
        converted_date = (last_updated_award_date - one_day).strftime(
            "%Y-%m-%dT00:00:00.000"
        )
        url = (
            f"{URLS['CONTRACTS']}?$limit={app_settings.secop_pagination_limit}&$offset={index}"
            "&$order=documento_proveedor&$where=es_pyme = 'Si' AND estado_contrato = 'Borrador' "
            f"AND ultima_actualizacion >= '{converted_date}' AND localizaci_n = 'Colombia, Bogotá, Bogotá'"
        )
        return httpx.get(url, headers=headers)

    url = (
        f"{URLS['CONTRACTS']}?$limit={app_settings.secop_pagination_limit}&$offset={index}"
        "&$order=documento_proveedor&$where=es_pyme = 'Si' AND estado_contrato = 'Borrador' "
        f"AND localizaci_n = 'Colombia, Bogotá, Bogotá'"
    )
    return httpx.get(url, headers=headers)


def get_or_create_award(entry, borrower_id, previous=False) -> tuple[int, str, str]:
    source_contract_id = entry.get("id_contrato", "")
    if source_contract_id in get_awards_list() or not source_contract_id:
        return 0, "", ""
    else:
        new_award = create_new_award(borrower_id, source_contract_id, entry)

        award_url = f"{URLS['AWARDS']}?id_del_portafolio={entry['proceso_de_compra']}"

        award_response = httpx.get(award_url, headers=headers)
        award_response_json = award_response.json()[0]

        new_award["description"] = award_response_json.get(
            "nombre_del_procedimiento", ""
        )
        new_award["award_date"] = award_response_json.get("fecha_adjudicacion", None)
        new_award["award_amount"] = award_response_json.get(
            "valor_total_adjudicacion", 0
        )
        new_award["source_data"] = award_response_json
        new_award["source_last_updated_at"] = award_response_json.get(
            "ultima_actualizacion)", None
        )
        new_award["contract_status"] = award_response_json.get(
            "estado_del_procedimiento", ""
        )
        new_award["title"] = award_response_json.get("nombre_del_procedimiento", "")

        if previous:
            new_award["contractperiod_startdate"] = entry.get(
                "fecha_de_inicio_del_contrato", None
            )
            new_award["contractperiod_enddate"] = entry.get(
                "fecha_de_fin_del_contrato", None
            )

        award_id = insert_award(new_award)
        return award_id, new_award["buyer_name"], new_award["title"]
