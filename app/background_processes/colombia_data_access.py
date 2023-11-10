from collections import Counter
from datetime import datetime, timedelta

from app.core.settings import app_settings
from app.exceptions import SkippedAwardError

from . import background_utils

URLS = {
    "CONTRACTS": "https://www.datos.gov.co/resource/jbjy-vk9h.json",
    "AWARDS": "https://www.datos.gov.co/resource/p6dx-8zbt.json",
    "BORROWER_EMAIL": "https://www.datos.gov.co/resource/vzyx-b5wf.json",
    "BORROWER": "https://www.datos.gov.co/resource/4ex9-j3n8.json?&es_pyme=SI",
}

headers = {"X-App-Token": app_settings.colombia_secop_app_token}


def create_new_award(
    source_contract_id: str,
    entry: dict,
    borrower_id: int = None,
    previous: bool = False,
) -> dict:
    """
    Create a new award and insert it into the database.

    :param source_contract_id: The unique identifier for the award's source contract.
    :type source_contract_id: str
    :param entry: The dictionary containing the award data.
    :type entry: dict
    :param borrower_id: The ID of the borrower associated with the award. (default: None)
    :type borrower_id: int, optional
    :param previous: Whether the award is a previous award or not. (default: False)
    :type previous: bool, optional

    :return: The newly created award data as a dictionary.
    :rtype: dict
    """

    proceso_de_compra = entry["proceso_de_compra"]
    proveedor_adjudicado = entry["proveedor_adjudicado"]

    new_award = {
        "source_contract_id": source_contract_id,
        "source_url": entry.get("urlproceso", {}).get("url", ""),
        "entity_code": entry.get("codigo_entidad", ""),
        "source_last_updated_at": entry.get("ultima_actualizacion", ""),
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

    award_url = (
        f"{URLS['AWARDS']}?$where=id_del_portafolio='{proceso_de_compra}'"
        f" AND nombre_del_proveedor='{proveedor_adjudicado}'"
    )

    award_response = background_utils.make_request_with_retry(award_url, headers)
    award_response_json = award_response.json()
    len_award_response_json = len(award_response_json)

    if len_award_response_json == 0:
        # We retry with nombre_del_proveedor set to No Adjudicado as sometimes the award information is available in
        # this endpoint but without the name of the supplier yet.
        award_url = f"{URLS['AWARDS']}?$where=id_del_portafolio='{proceso_de_compra}' AND nombre_del_proveedor='No " \
                    f"Adjudicado' "
        award_response = background_utils.make_request_with_retry(award_url, headers)
        award_response_json = award_response.json()
        if not award_response_json:
            raise SkippedAwardError(
                f"[{previous=}] Non awards found from {award_url}"
            )
    elif len_award_response_json > 1:
        # If there is more than one award for the given supplier, we check if the relevant data is the same for all.
        award_info = set()
        for award in award_response_json:
            award_info.add((award.get("descripci_n_del_procedimiento", ""), award.get("fecha_adjudicacion", None),
                            award.get("estado_del_procedimiento", ""), award.get("nombre_del_procedimiento", "")))
        if len(award_info) > 1:
            raise SkippedAwardError(
                f"[{previous=}] {len_award_response_json} non equal awards from {award_url} "
                f"(response={award_response_json})"
            )

    remote_award = award_response_json[0]

    new_award["description"] = remote_award.get("descripci_n_del_procedimiento", "")
    new_award["award_date"] = remote_award.get("fecha_adjudicacion", None)
    new_award["source_data_awards"] = remote_award

    new_award["contract_status"] = remote_award.get("estado_del_procedimiento", "")
    new_award["title"] = remote_award.get("nombre_del_procedimiento", "")

    if borrower_id:
        new_award["borrower_id"] = borrower_id

    return new_award


def get_new_contracts(index: int, from_date, until_date=None):
    offset = index * app_settings.secop_pagination_limit
    delta = timedelta(days=app_settings.secop_default_days_from_ultima_actualizacion)
    date_format = "%Y-%m-%dT%H:%M:%S.000"
    converted_date = (datetime.now() - delta).strftime(date_format)

    if from_date and not until_date:
        delta = timedelta(seconds=1)
        converted_date = (from_date + delta).strftime(date_format)

    base_url = (
        f"{URLS['CONTRACTS']}?$limit={app_settings.secop_pagination_limit}&$offset={offset}"
        "&$order=ultima_actualizacion desc null last&$where=es_pyme = 'Si' "
        f"AND localizaci_n = 'Colombia, Bogotá, Bogotá'"
    )

    if from_date and until_date:
        url = (
            f"{base_url}"
            f"AND ultima_actualizacion >= '{from_date}' "
            f"AND ultima_actualizacion < '{until_date}' "
        )
    else:
        url = (
            f"{base_url}"
            f"AND estado_contrato = 'Borrador' AND ultima_actualizacion >= '{converted_date}'"
        )

    return background_utils.make_request_with_retry(url, headers)


def get_previous_contracts(documento_proveedor):
    """
    Get previous contracts data for the given document provider from the source API.

    :param documento_proveedor: The document provider to get previous contracts data for.
    :type documento_proveedor: str

    :return: The response object containing the previous contracts data.
    :rtype: httpx.Response
    """

    url = f"{URLS['CONTRACTS']}?$where=documento_proveedor = '{documento_proveedor}' AND fecha_de_firma IS NOT NULL"

    return background_utils.make_request_with_retry(url, headers)


def get_source_contract_id(entry):
    """
    Get the source contract ID from the given entry data.

    :param entry: The dictionary containing the award data.
    :type entry: dict

    :return: The source contract ID.
    :rtype: str
    """

    source_contract_id = entry.get("id_contrato", "")

    if not source_contract_id:
        raise SkippedAwardError(f"No id_contrato in {entry=}")

    return source_contract_id


def create_new_borrower(
    borrower_identifier: str, documento_proveedor: str, entry: dict
) -> dict:
    """
    Create a new borrower and insert it into the database.

    :param borrower_identifier: The unique identifier for the borrower.
    :type borrower_identifier: str
    :param documento_proveedor: The document provider for the borrower.
    :type documento_proveedor: str
    :param entry: The dictionary containing the borrower data.
    :type entry: dict

    :return: The newly created borrower data as a dictionary.
    :rtype: dict
    """

    borrower_url = (
        f"{URLS['BORROWER']}&nit_entidad={documento_proveedor}"
        f"&codigo_entidad={entry.get('codigo_proveedor', '')}"
    )
    borrower_response = background_utils.make_request_with_retry(borrower_url, headers)
    borrower_response_json = borrower_response.json()
    len_borrower_response_json = len(borrower_response_json)

    if len_borrower_response_json > 1:
        raise SkippedAwardError(
            f"{len_borrower_response_json} borrowers for {documento_proveedor=} "
            f"({entry=} response={borrower_response_json})"
        )

    remote_borrower = borrower_response_json[0]
    email = get_email(documento_proveedor, entry)

    new_borrower = {
        "borrower_identifier": borrower_identifier,
        "legal_name": remote_borrower.get("nombre_entidad", ""),
        "email": email,
        "address": "Direccion: {}\nCiudad: {}\nProvincia: {}\nEstado: {}".format(
            remote_borrower.get("direccion", "No provisto"),
            remote_borrower.get("ciudad", "No provisto"),
            remote_borrower.get("provincia", "No provisto"),
            remote_borrower.get("estado", "No provisto"),
        ),
        "legal_identifier": remote_borrower.get("nit_entidad", ""),
        "type": remote_borrower.get("tipo_organizacion", ""),
        "source_data": remote_borrower,
    }

    return new_borrower


def get_email(documento_proveedor, entry) -> str:
    """
    Get the email address for the borrower based on the given document provider and entry data.

    :param documento_proveedor: The document provider for the borrower.
    :type documento_proveedor: str
    :param entry: The dictionary containing the borrower data.
    :type entry: dict

    :return: The email address of the borrower.
    :rtype: str
    """

    borrower_email_url = f"{URLS['BORROWER_EMAIL']}?nit={documento_proveedor}"
    borrower_response_email = background_utils.make_request_with_retry(
        borrower_email_url, headers
    )
    borrower_response_email_json = borrower_response_email.json()
    len_borrower_response_email_json = len(borrower_response_email_json)

    if len_borrower_response_email_json == 0:
        raise SkippedAwardError(
            f"0 borrower emails from {borrower_email_url} "
            f"(response={borrower_response_email_json})"
        )

    remote_email = borrower_response_email_json[0]
    email = remote_email.get("correo_entidad", "")

    if len_borrower_response_email_json > 1:
        email = Counter(borrower_email['correo_entidad']
                        for borrower_email in borrower_response_email_json).most_common(1)[0][0]

    if not background_utils.is_valid_email(email):
        raise SkippedAwardError(
            f"Invalid borrower email ({email=} {entry=})"
        )

    return email


def get_documento_proveedor(entry) -> str:
    """
    Get the document provider from the given entry data.

    :param entry: The dictionary containing the borrower data.
    :type entry: dict

    :return: The document provider for the borrower.
    :rtype: str
    """

    documento_proveedor = entry.get("documento_proveedor", None)
    if not documento_proveedor or documento_proveedor == "No Definido":
        raise SkippedAwardError(
            f"No borrower identifier in {documento_proveedor=} ({entry=})"
        )

    return documento_proveedor
