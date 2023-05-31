import os
from datetime import datetime

import httpx
from dotenv import dotenv_values

CONTRACTS_URL = "https://www.datos.gov.co/resource/jbjy-vk9h.json"
AWARDS_URL = "https://www.datos.gov.co/resource/p6dx-8zbt.json"
BORROWER_EMAIL_URL = "https://www.datos.gov.co/resource/vzyx-b5wf.json"
BORROWER_URL = "https://www.datos.gov.co/resource/4ex9-j3n8.json"

config_env = {
    **dotenv_values(".env"),
    **os.environ,
}  # config are loading separately from main app in order to avoid package dependencies

secop_app_token: str = config_env.get("SECOP_APP_TOKEN", None)
backend_url: str = config_env.get("BACKEND_URL", None)
headers = {"X-App-Token": secop_app_token}


def get_awards_contracting_process_ids():
    return httpx.get(f"{backend_url}/awards/get-awards-contracting-process-ids/").json()


existing_awards_contracting_process_id = get_awards_contracting_process_ids()


def get_new_contracts():
    last_fetch_date = None
    # last_fech_date = httpx.get(f"{backend_url}/awards/last/").json()["created_at"]

    if last_fetch_date:
        converted_date = datetime.strptime(last_fetch_date, "%Y-%m-%dT%H:%M:%S.%f%z").strftime("%Y-%m-%dT00:00:00.000")
        print(converted_date)
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


def complete_borrower(entry):
    borrower_url_email = f"{BORROWER_EMAIL_URL}?nit={entry['documento_proveedor']}"
    borrower_response_email = httpx.get(borrower_url_email, headers=headers)
    borrower_response_email_json = borrower_response_email.json()[0]
    if not borrower_response_email_json["correo_entidad"]:
        return

    borrower_url = f"{BORROWER_URL}?nit_entidad={entry['documento_proveedor']}"

    borrower_response = httpx.get(borrower_url, headers=headers)
    borrower_response_json = borrower_response.json()[0]

    fetched_borrower = {}
    fetched_borrower["borrower_identifier"] = entry["nit_entidad"]
    fetched_borrower["legal_name"] = entry["nombre_entidad"]
    fetched_borrower["email"] = borrower_response_email_json["correo_entidad"]
    fetched_borrower["address"] = (
        "Direccion: "
        + borrower_response_json["direccion"]
        + "Ciudad: "
        + borrower_response_json["ciudad"]
        + "provincia"
        + borrower_response_json["provincia"]
        + "estado"
        + borrower_response_json["estado"]
    )

    fetched_borrower["legal_identifier"] = entry["nit_entidad"]
    fetched_borrower["type"] = borrower_response_json["tipo_organizacion"]
    endpoint_response = httpx.post(f"{backend_url}/borrowers/", json=fetched_borrower)
    return endpoint_response.json()["id"]


def complete_award(entry, borrower_id):
    if entry["proceso_de_compra"] in existing_awards_contracting_process_id:
        return
    fetched_award = {}
    fetched_award["contracting_process_id"] = entry["proceso_de_compra"]
    fetched_award["award_currency"] = "Colombian Peso"
    fetched_award["buyer_name"] = entry["nombre_entidad"]
    fetched_award["source_url"] = entry["urlproceso"]["url"]
    fetched_award["entity_code"] = entry["codigo_entidad"]
    fetched_award["previous"] = False
    fetched_award["procurement_method"] = entry["modalidad_de_contratacion"]
    fetched_award["procurement_category"] = entry["tipo_de_contrato"]
    fetched_award["source_data"] = entry["urlproceso"]
    fetched_award["payment_method"] = entry["habilita_pago_adelantado"] + " " + entry["valor_de_pago_adelantado"]

    award_url = f"{AWARDS_URL}?id_del_portafolio={entry['proceso_de_compra']}"

    award_response = httpx.get(award_url, headers=headers)
    award_response_json = award_response.json()[0]

    fetched_award["award_amount"] = award_response_json["valor_total_adjudicacion"]
    fetched_award["title"] = award_response_json["nombre_del_procedimiento"]
    fetched_award["description"] = award_response_json["nombre_del_procedimiento"]
    fetched_award["award_date"] = award_response_json.get("fecha_adjudicacion", None)
    print(entry)
    fetched_award["contractperiod_startdate"] = entry.get("fecha_de_inicio_del_contrato", None)
    fetched_award["contractperiod_enddate"] = entry.get("fecha_de_fin_del_contrato", None)

    fetched_award["contract_status"] = award_response_json["estado_del_procedimiento"]
    fetched_award["source_last_updated_at"] = award_response_json["fecha_de_ultima_publicaci"]
    fetched_award["borrower_id"] = borrower_id
    httpx.post(f"{backend_url}/awards/", json=fetched_award)
