from collections import Counter
from datetime import datetime, timedelta
from typing import Any

import httpx

from app import sources, util
from app.exceptions import SkippedAwardError
from app.settings import app_settings

URLS = {
    "CONTRACTS": "https://www.datos.gov.co/resource/jbjy-vk9h.json",
    "AWARDS": "https://www.datos.gov.co/resource/p6dx-8zbt.json",
    "BORROWER_EMAIL": "https://www.datos.gov.co/resource/vzyx-b5wf.json",
    "BORROWER": "https://www.datos.gov.co/resource/4ex9-j3n8.json",
}

HEADERS = {"X-App-Token": app_settings.colombia_secop_app_token}

SUPPLIER_TYPE_TO_EXCLUDE = "persona natural colombiana"


def _get_remote_contract(
    proceso_de_compra: str, proveedor_adjudicado: str, previous=False
) -> tuple[list[dict[str, str]], str]:
    params = f"proceso_de_compra='{proceso_de_compra}' AND documento_proveedor='{proveedor_adjudicado}'"
    contract_url = f"{URLS['CONTRACTS']}?$where={params}"
    if previous:
        contract_url = f"{contract_url} AND fecha_de_firma IS NOT NULL"
    return util.loads(sources.make_request_with_retry(contract_url, HEADERS)), contract_url


def get_procurement_categories():
    # from https://www.datos.gov.co/resource/p6dx-8zbt.json?$query=SELECT distinct `tipo_de_contrato`
    return [
        "Comodato",
        "Empréstito",
        "Venta inmuebles",
        "Seguros",
        "Interventoría",
        "Arrendamiento de muebles",
        "Negocio fiduciario",
        "Concesión",
        "No",
        "Asociación Público Privada",
        "No Especificado",
        "Otro",
        "Acuerdo Marco de Precios",
        "Arrendamiento de inmuebles",
        "Compraventa",
        "Comisión",
        "Prestación de servicios",
        "Decreto 092 de 2017",
        "Venta muebles",
        "Operaciones de Crédito Público",
        "Suministros",
        "Obra",
        "Servicios financieros",
        "Acuerdo de cooperación",
        "Consultoría",
    ]


def get_award(
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

    proceso_de_compra = entry["id_del_portafolio"]
    proveedor_adjudicado = entry["nit_del_proveedor_adjudicado"]

    new_award = {
        "source_url": entry.get("urlproceso", {}).get("url", ""),
        "entity_code": entry.get("nit_entidad", ""),
        "source_last_updated_at": entry.get("fecha_de_ultima_publicaci", None),
        "procurement_method": entry.get("modalidad_de_contratacion", ""),
        "buyer_name": entry.get("entidad", ""),
        "contracting_process_id": proceso_de_compra,
        "procurement_category": entry.get("tipo_de_contrato", ""),
        "previous": previous,
        "source_data_awards": entry,
        "description": entry.get("descripci_n_del_procedimiento", ""),
        "award_date": entry.get("fecha_adjudicacion", None),
        "contract_status": entry.get("estado_del_procedimiento", ""),
        "title": entry.get("nombre_del_procedimiento", ""),
    }

    contract_response_json, contract_url = _get_remote_contract(proceso_de_compra, proveedor_adjudicado, previous)

    if not contract_response_json:
        # Retry with nombre_del_proveedor="No Adjudicado", in case award data is available, but not the supplier name.
        contract_response_json, contract_url = _get_remote_contract(proceso_de_compra, "No Adjudicado")
        if not contract_response_json:
            raise SkippedAwardError("No remote contracts found", url=contract_url, data={"previous": previous})

    remote_contract = contract_response_json[0]
    new_award["payment_method"] = {
        "habilita_pago_adelantado": remote_contract.get("habilita_pago_adelantado", ""),
        "valor_de_pago_adelantado": remote_contract.get("valor_de_pago_adelantado", ""),
        "valor_facturado": remote_contract.get("valor_facturado", ""),
        "valor_pendiente_de_pago": remote_contract.get("valor_pendiente_de_pago", ""),
        "valor_pagado": remote_contract.get("valor_pagado", ""),
    }
    new_award["contractperiod_startdate"] = (remote_contract.get("fecha_de_inicio_del_contrato", None),)
    new_award["contractperiod_enddate"] = (remote_contract.get("fecha_de_fin_del_contrato", None),)
    new_award["award_amount"] = remote_contract.get("valor_del_contrato", "")
    new_award["source_data_contracts"] = remote_contract
    new_award["source_contract_id"] = remote_contract.get("id_contrato", "")

    if not new_award["source_contract_id"]:
        raise SkippedAwardError("Missing id_contrato", data=remote_contract)

    if borrower_id:
        new_award["borrower_id"] = borrower_id
    return new_award


def get_new_awards(index: int, from_date: datetime, until_date: datetime | None = None) -> httpx.Response:
    offset = index * app_settings.secop_pagination_limit
    date_format = "%Y-%m-%dT%H:%M:%S.000"

    base_url = (
        f"{URLS['AWARDS']}?$limit={app_settings.secop_pagination_limit}&$offset={offset}"
        "&$order=fecha_de_ultima_publicaci desc null last&$where="
        " caseless_eq(`adjudicado`, 'Si')"
    )

    if from_date and until_date:
        url = (
            f"{base_url} AND ((fecha_de_ultima_publicaci >= '{from_date.strftime(date_format)}' "
            f"AND fecha_de_ultima_publicaci < '{until_date.strftime(date_format)}') OR "
            f"(fecha_adjudicacion >= '{from_date.strftime(date_format)}' "
            f"AND fecha_adjudicacion < '{until_date.strftime(date_format)}'))"
        )
    else:
        if from_date:
            converted_date = from_date + timedelta(seconds=1)
        else:
            converted_date = datetime.now() - timedelta(days=app_settings.secop_default_days_from_ultima_actualizacion)
        url = (
            f"{base_url} AND (fecha_de_ultima_publicaci >= '{converted_date.strftime(date_format)}' "
            f"OR fecha_adjudicacion >= '{converted_date.strftime(date_format)}')"
        )

    return sources.make_request_with_retry(url, HEADERS)


def get_award_by_id_and_supplier(award_id: str, supplier_id: str) -> httpx.Response:
    url = f"{URLS['AWARDS']}?$where=nit_del_proveedor_adjudicado = '{supplier_id}' AND id_adjudicacion = '{award_id}'"

    return sources.make_request_with_retry(url, HEADERS)


def get_previous_awards(documento_proveedor: str) -> httpx.Response:
    """
    Get previous contracts data for the given document provider from the source API.

    :param documento_proveedor: The document provider to get previous contracts data for.
    :return: The response object containing the previous awards data.
    """

    url = f"{URLS['AWARDS']}?$where=nit_del_proveedor_adjudicado = '{documento_proveedor}'"

    return sources.make_request_with_retry(url, HEADERS)


def get_borrower(borrower_identifier: str, documento_proveedor: str, entry: dict[str, str]) -> dict[str, str]:
    """
    Get the borrower information from the source

    :param borrower_identifier: The unique identifier for the borrower.
    :param documento_proveedor: The document provider for the borrower.
    :param entry: The dictionary containing the borrower data.
    :return: The newly created borrower data as a dictionary.
    """

    borrower_url = (
        f"{URLS['BORROWER']}?nit_entidad={documento_proveedor}&codigo_entidad={entry.get('codigoproveedor', '')}"
    )
    borrower_response_json = util.loads(sources.make_request_with_retry(borrower_url, HEADERS))
    len_borrower_response_json = len(borrower_response_json)

    if len_borrower_response_json != 1:
        raise SkippedAwardError(
            "Multiple remote borrowers found",
            url=borrower_url,
            data={"response": borrower_response_json, "count": len_borrower_response_json},
        )

    remote_borrower = borrower_response_json[0]
    email = get_email(documento_proveedor)

    if remote_borrower.get("tipo_organizacion", "").lower() == SUPPLIER_TYPE_TO_EXCLUDE:
        raise SkippedAwardError(
            f"Borrower is {SUPPLIER_TYPE_TO_EXCLUDE}",
            url=borrower_url,
            data={"response": borrower_response_json},
        )

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
        "is_msme": remote_borrower.get("es_pyme", "").lower() == "si",
    }

    return new_borrower


def _get_email(borrower_response: dict):
    return (
        borrower_response.get("correo_entidad")
        if "correo_entidad" in borrower_response
        else borrower_response.get("correo_electr_nico", "")
    )


def get_email(documento_proveedor: str) -> str:
    """
    Get the email address for the borrower based on the given document provider.

    :param documento_proveedor: The document provider for the borrower.
    :return: The email address of the borrower.
    """

    borrower_email_url = f"{URLS['BORROWER_EMAIL']}?nit={documento_proveedor}"
    borrower_response_email_json = util.loads(sources.make_request_with_retry(borrower_email_url, HEADERS))
    len_borrower_response_email_json = len(borrower_response_email_json)

    if len_borrower_response_email_json == 0:
        raise SkippedAwardError("No remote borrower emails found", url=borrower_email_url)

    remote_email: dict[str, str] = borrower_response_email_json[0]
    email = _get_email(remote_email)

    if len_borrower_response_email_json > 1:
        email = Counter(_get_email(borrower_email) for borrower_email in borrower_response_email_json).most_common(1)[
            0
        ][0]

    if not sources.is_valid_email(email):
        raise SkippedAwardError(
            "Invalid remote borrower email",
            url=borrower_email_url,
            data={"response": borrower_response_email_json, "email": email},
        )

    return email


def get_documento_proveedor(entry: dict[str, str]) -> str:
    """
    Get the document provider from the given entry data.

    :param entry: The dictionary containing the borrower data.
    :return: The document provider for the borrower.
    """

    documento_proveedor = entry.get("nit_del_proveedor_adjudicado", None)
    if not documento_proveedor or documento_proveedor == "No Definido":
        raise SkippedAwardError("Missing documento_proveedor", data=entry)

    return documento_proveedor
