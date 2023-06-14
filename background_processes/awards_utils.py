from contextlib import contextmanager
from datetime import datetime, timedelta

from sqlalchemy import desc
from sqlalchemy.orm.session import Session

from app.db.session import app_settings, get_db
from app.schema.core import Award

from . import background_utils
from .background_config import URLS


def get_existing_award(source_contract_id: str, session: Session):
    award = (
        session.query(Award)
        .filter(Award.source_contract_id == source_contract_id)
        .first()
    )

    return award


def get_last_updated_award_date():
    with contextmanager(get_db)() as session:
        award = (
            session.query(Award).order_by(desc(Award.source_last_updated_at)).first()
        )
    if not award:
        return None

    return award.source_last_updated_at


def insert_award(award: Award, session: Session):
    obj_db = Award(**award)
    obj_db.created_at = datetime.utcnow()
    obj_db.missing_data = background_utils.get_missing_data_keys(award)

    session.add(obj_db)
    session.flush()
    return obj_db


def create_new_award(source_contract_id: str, previous: bool, entry: dict) -> dict:
    return {
        "source_contract_id": source_contract_id,
        "source_url": entry.get("urlproceso", {}).get("url", ""),
        "entity_code": entry.get("codigo_entidad", ""),
        "source_last_updated_at": entry.get("ultima_actualizacion", ""),
        "award_amount": entry.get("valor_del_contrato", ""),
        "contractperiod_startdate": entry.get("fecha_de_inicio_del_contrato", None),
        "contractperiod_enddate": entry.get("fecha_de_fin_del_contrato", None),
        "procurement_method": entry.get("modalidad_de_contratacion", ""),
        "buyer_name": entry.get("nombre_entidad", ""),
        "contracting_process_id": entry.get("proceso_de_compra", ""),
        "procurement_category": entry.get("tipo_de_contrato", ""),
        "previous": previous,
        "payment_method": {
            "habilita_pago_adelantado": entry.get("habilita_pago_adelantado", ""),
            "valor_de_pago_adelantado": entry.get("valor_de_pago_adelantado", ""),
            "valor_facturado": entry.get("valor_facturado", ""),
            "valor_pendiente_de_pago": entry.get("valor_pendiente_de_pago", ""),
            "valor_pagado": entry.get("valor_pagado", ""),
        },
        "source_data_contracts": entry,
    }


def get_new_contracts(index: int, last_updated_award_date):
    offset = index * app_settings.secop_pagination_limit
    delta = timedelta(days=app_settings.secop_default_days_from_ultima_actualizacion)
    converted_date = (datetime.now() - delta).strftime("%Y-%m-%dT00:00:00.000")

    if last_updated_award_date:
        delta = timedelta(days=1)
        converted_date = (last_updated_award_date - delta).strftime(
            "%Y-%m-%dT00:00:00.000"
        )

    url = (
        f"{URLS['CONTRACTS']}?$limit={app_settings.secop_pagination_limit}&$offset={offset}"
        "&$order=ultima_actualizacion&$where=es_pyme = 'Si' AND estado_contrato = 'Borrador' "
        f"AND ultima_actualizacion >= '{converted_date}' AND localizaci_n = 'Colombia, Bogotá, Bogotá'"
    )

    return background_utils.make_request_with_retry(url)


def get_previous_contracts(documento_proveedor):
    url = f"{URLS['CONTRACTS']}?$where=documento_proveedor = '{documento_proveedor}' AND fecha_de_firma IS NOT NULL"

    return background_utils.make_request_with_retry(url)


def create_award(entry, session: Session, borrower_id=None, previous=False) -> Award:
    source_contract_id = entry.get("id_contrato", "")

    if not source_contract_id:
        background_utils.raise_sentry_error("Skipping Award - No id_contrato", entry)

    # if award already exists
    if get_existing_award(source_contract_id, session):
        background_utils.raise_sentry_error(
            f"Skipping Award [previous {previous}] - Already exists on Database", entry
        )

    new_award = create_new_award(source_contract_id, previous, entry)
    award_url = (
        f"{URLS['AWARDS']}?$where=id_del_portafolio='{entry['proceso_de_compra']}'"
        f" AND nombre_del_proveedor='{entry['proveedor_adjudicado']}'"
    )

    award_response = background_utils.make_request_with_retry(award_url)

    if len(award_response.json()) > 1 or len(award_response.json()) == 0:
        error_data = {
            "entry": entry,
            "proveedor_adjudicado": entry["proveedor_adjudicado"],
            "id_del_portafolio": entry["proceso_de_compra"],
            "response": award_response.json(),
        }
        background_utils.raise_sentry_error(
            (
                f"Skipping Award [previous {previous}]"
                " - Zero or more than one results for 'proceso_de_compra' and 'proveedor_adjudicado'"
            ),
            error_data,
        )

    award_response_json = award_response.json()[0]

    new_award["description"] = award_response_json.get(
        "descripci_n_del_procedimiento", ""
    )
    new_award["award_date"] = award_response_json.get("fecha_adjudicacion", None)
    new_award["source_data_awards"] = award_response_json

    new_award["contract_status"] = award_response_json.get(
        "estado_del_procedimiento", ""
    )
    new_award["title"] = award_response_json.get("nombre_del_procedimiento", "")

    if borrower_id:
        new_award["borrower_id"] = borrower_id

    award = insert_award(new_award, session)

    return award
