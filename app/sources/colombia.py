from collections import Counter
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote_plus

import httpx

from app import sources
from app.exceptions import SkippedAwardError
from app.settings import app_settings

URLS = {
    "CONTRACTS": "https://www.datos.gov.co/resource/jbjy-vk9h.json",
    "AWARDS": "https://www.datos.gov.co/resource/p6dx-8zbt.json",
    "BORROWER_EMAIL": "https://www.datos.gov.co/resource/vzyx-b5wf.json",
    "BORROWER": "https://www.datos.gov.co/resource/4ex9-j3n8.json?&es_pyme=SI",
}

HEADERS = {"X-App-Token": app_settings.colombia_secop_app_token}


def _get_remote_award(proceso_de_compra: str, proveedor_adjudicado: str) -> tuple[list[dict[str, str]], str]:
    params = quote_plus(f"id_del_portafolio='{proceso_de_compra}' AND nombre_del_proveedor='{proveedor_adjudicado}'")
    award_url = f"{URLS['AWARDS']}?$where={params}"
    return sources.make_request_with_retry(award_url, HEADERS).json(), award_url


def get_award(
    source_contract_id: str,
    entry: dict[str, Any],
    borrower_id: int | None = None,
    previous: bool = False,
) -> dict[str, str | None]:
    """
    Create a new award and insert it into the database.

    :param source_contract_id: The unique identifier for the award's source contract.
    :param entry: The dictionary containing the award data.
    :param borrower_id: The ID of the borrower associated with the award. (default: None)
    :param previous: Whether the award is a previous award or not. (default: False)
    :return: The newly created award data as a dictionary.
    """

    proceso_de_compra = entry["proceso_de_compra"]
    proveedor_adjudicado = entry["proveedor_adjudicado"]

    new_award = {
        "source_contract_id": source_contract_id,
        "source_url": entry.get("urlproceso", {}).get("url", ""),
        "entity_code": entry.get("codigo_entidad", ""),
        "source_last_updated_at": entry.get("ultima_actualizacion", None),
        "award_amount": entry.get("valor_del_contrato", ""),
        "contractperiod_startdate": entry.get("fecha_de_inicio_del_contrato", None),
        "contractperiod_enddate": entry.get("fecha_de_fin_del_contrato", None),
        "procurement_method": entry.get("modalidad_de_contratacion", ""),
        "buyer_name": entry.get("nombre_entidad", ""),
        "contracting_process_id": proceso_de_compra,
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

    award_response_json, award_url = _get_remote_award(proceso_de_compra, proveedor_adjudicado)

    if not award_response_json:
        # Retry with nombre_del_proveedor="No Adjudicado", in case award data is available, but not the supplier name.
        award_response_json, award_url = _get_remote_award(proceso_de_compra, "No Adjudicado")
        if not award_response_json:
            raise SkippedAwardError(f"[{previous=}] 0 awards found", url=award_url)

    # It's okay if there are many awards, as long as the award data is consistent.
    remote_awards = set()
    for award in award_response_json:
        remote_awards.add(
            (
                award.get("descripci_n_del_procedimiento", ""),
                award.get("fecha_adjudicacion", None),
                award.get("estado_del_procedimiento", ""),
                award.get("nombre_del_procedimiento", ""),
            )
        )
    if len(remote_awards) > 1:
        raise SkippedAwardError(
            f"[{previous=}] {len(award_response_json)} awards ({len(remote_awards)} unique)",
            data=award_response_json,
            url=award_url,
        )

    remote_award = remote_awards.pop()
    new_award["description"] = remote_award[0]
    new_award["award_date"] = remote_award[1]
    new_award["contract_status"] = remote_award[2]
    new_award["title"] = remote_award[3]
    new_award["source_data_awards"] = award_response_json[0]

    if borrower_id:
        new_award["borrower_id"] = borrower_id

    return new_award


def get_new_contracts(index: int, from_date: datetime, until_date: datetime | None = None) -> httpx.Response:
    offset = index * app_settings.secop_pagination_limit
    date_format = "%Y-%m-%dT%H:%M:%S.000"

    base_url = (
        f"{URLS['CONTRACTS']}?$limit={app_settings.secop_pagination_limit}&$offset={offset}"
        "&$order=ultima_actualizacion desc null last&$where=es_pyme = 'Si' "
        f"AND localizaci_n = 'Colombia, Bogotá, Bogotá'"
    )

    if from_date and until_date:
        url = (
            f"{base_url} AND ultima_actualizacion >= '{from_date.strftime(date_format)}' "
            f"AND ultima_actualizacion < '{until_date.strftime(date_format)}' "
        )
    else:
        if from_date:
            converted_date = from_date + timedelta(seconds=1)
        else:
            converted_date = datetime.now() - timedelta(days=app_settings.secop_default_days_from_ultima_actualizacion)
        url = (
            f"{base_url} AND caseless_not_one_of( `estado_contrato`, 'Cancelado', 'Cerrado', 'cedido', "
            f"'Suspendido', 'terminado') "
            f"AND ultima_actualizacion >= '{converted_date.strftime(date_format)}'"
        )

    return sources.make_request_with_retry(url, HEADERS)


def get_contract_by_contract_and_supplier(contract_id: str, supplier_id: str) -> httpx.Response:
    url = f"{URLS['CONTRACTS']}?$where=documento_proveedor = '{supplier_id}' AND id_contrato = '{contract_id}'"

    return sources.make_request_with_retry(url, HEADERS)


def get_previous_contracts(documento_proveedor: str) -> httpx.Response:
    """
    Get previous contracts data for the given document provider from the source API.

    :param documento_proveedor: The document provider to get previous contracts data for.
    :return: The response object containing the previous contracts data.
    """

    url = f"{URLS['CONTRACTS']}?$where=documento_proveedor = '{documento_proveedor}' AND fecha_de_firma IS NOT NULL"

    return sources.make_request_with_retry(url, HEADERS)


def get_source_contract_id(entry: dict[str, str]) -> str:
    """
    Get the source contract ID from the given entry data.

    :param entry: The dictionary containing the award data.
    :return: The source contract ID.
    """

    source_contract_id = entry.get("id_contrato", "")

    if not source_contract_id:
        raise SkippedAwardError("No id_contrato in source data", data=entry)

    return source_contract_id


def get_borrower(borrower_identifier: str, documento_proveedor: str, entry: dict[str, str]) -> dict[str, str]:
    """
    Get the borrower information from the source

    :param borrower_identifier: The unique identifier for the borrower.
    :param documento_proveedor: The document provider for the borrower.
    :param entry: The dictionary containing the borrower data.
    :return: The newly created borrower data as a dictionary.
    """

    borrower_url = (
        f"{URLS['BORROWER']}&nit_entidad={documento_proveedor}&codigo_entidad={entry.get('codigo_proveedor', '')}"
    )
    borrower_response = sources.make_request_with_retry(borrower_url, HEADERS)
    borrower_response_json = borrower_response.json()
    len_borrower_response_json = len(borrower_response_json)

    if len_borrower_response_json != 1:
        raise SkippedAwardError(
            f"{len_borrower_response_json} borrowers for the given borrower",
            data=borrower_response_json,
            url=borrower_url,
        )

    remote_borrower = borrower_response_json[0]
    email = get_email(documento_proveedor)

    new_borrower = {
        "borrower_identifier": borrower_identifier,
        "legal_name": remote_borrower.get("nombre_entidad", ""),
        "email": email,
        "address": (
            f"Direccion: {remote_borrower.get('direccion', 'No provisto')}\n"
            f"Ciudad: {remote_borrower.get('ciudad', 'No provisto')}\n"
            f"Provincia: {remote_borrower.get('provincia', 'No provisto')}\n"
            f"Estado: {remote_borrower.get('estado', 'No provisto')}"
        ),
        "legal_identifier": remote_borrower.get("nit_entidad", ""),
        "type": remote_borrower.get("tipo_organizacion", ""),
        "source_data": remote_borrower,
    }

    return new_borrower


def get_email(documento_proveedor: str) -> str:
    """
    Get the email address for the borrower based on the given document provider.

    :param documento_proveedor: The document provider for the borrower.
    :return: The email address of the borrower.
    """

    borrower_email_url = f"{URLS['BORROWER_EMAIL']}?nit={documento_proveedor}"
    borrower_response_email = sources.make_request_with_retry(borrower_email_url, HEADERS)
    borrower_response_email_json = borrower_response_email.json()
    len_borrower_response_email_json = len(borrower_response_email_json)

    if len_borrower_response_email_json == 0:
        raise SkippedAwardError("0 borrower emails found for the given borrower", url=borrower_email_url)

    remote_email: dict[str, str] = borrower_response_email_json[0]
    email = remote_email.get("correo_entidad", "")

    if len_borrower_response_email_json > 1:
        email = Counter(
            borrower_email["correo_entidad"] for borrower_email in borrower_response_email_json
        ).most_common(1)[0][0]

    if not sources.is_valid_email(email):
        raise SkippedAwardError("Invalid borrower email", data=borrower_response_email_json, url=borrower_email_url)

    return email


def get_documento_proveedor(entry: dict[str, str]) -> str:
    """
    Get the document provider from the given entry data.

    :param entry: The dictionary containing the borrower data.
    :return: The document provider for the borrower.
    """

    documento_proveedor = entry.get("documento_proveedor", None)
    if not documento_proveedor or documento_proveedor == "No Definido":
        raise SkippedAwardError(f"No borrower identifier in {documento_proveedor=} ({entry=})")

    return documento_proveedor
