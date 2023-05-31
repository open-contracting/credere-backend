import os
from datetime import datetime, time

import requests
from dotenv import dotenv_values

config_env = {
    **dotenv_values(".env"),
    **os.environ,
}  # config are loading separately from main app in order to avoid package dependencies

secop_app_token: str = config_env.get("SECOP_APP_TOKEN", None)
backend_url: str = config_env.get("BACKEND_URL", None)
headers = {"X-App-Token": secop_app_token}


last_updated_date = requests.get(f"{backend_url}/awards/last/")
print(last_updated_date.json()["created_at"])


today = datetime.now().date()
eight_am = time(8, 0, 0)
today_at_eight_am = datetime.combine(today, eight_am)
# formatted_datetime = last_updated_date.json()["created_at"].strftime("%Y-%m-%dT00:00:00.000")
testing = "2023-05-29T00:00:00.000"
url = (
    "https://www.datos.gov.co/resource/jbjy-vk9h.json?$where=es_pyme = 'Si' AND estado_contrato = 'Borrador' "
    f"AND ultima_actualizacion >= '{testing}' AND localizaci_n = 'Colombia, Bogotá, Bogotá'"
)


response = requests.get(url, headers=headers)
response_json = response.json()


def complete_borrower(entry):
    borrower_url_email = f"https://www.datos.gov.co/resource/vzyx-b5wf.json?nit={entry['documento_proveedor']}"

    borrower_response_email = requests.get(borrower_url_email, headers=headers)
    borrower_response_email_json = borrower_response_email.json()[0]

    borrower_url = f"https://www.datos.gov.co/resource/4ex9-j3n8.json?nit_entidad={entry['documento_proveedor']}"

    borrower_response = requests.get(borrower_url, headers=headers)
    borrower_response_json = borrower_response.json()[0]

    fetched_borrower = {}
    fetched_borrower["borrower_identifier"] = entry["nit_entidad"]  # contracts
    fetched_borrower["legal_name"] = entry["nombre_entidad"]
    fetched_borrower["email"] = borrower_response_email_json["correo_entidad"]  # borrower
    fetched_borrower["address"] = (
        "Direccion: "
        + borrower_response_json["direccion"]
        + "Ciudad: "
        + borrower_response_json["ciudad"]
        + "provincia"
        + borrower_response_json["provincia"]
        + "estado"
        + borrower_response_json["estado"]
    )  # borrower

    fetched_borrower["legal_identifier"] = entry["nit_entidad"]  # contract
    fetched_borrower["type"] = borrower_response_json["tipo_organizacion"]  # borrower
    endpoint_response = requests.post(f"{backend_url}/borrowers/", json=fetched_borrower)
    return endpoint_response.json()["id"]


def complete_award(entry, borrower_id):
    fetched_award = {}
    fetched_award["proceso_de_compra"] = entry["proceso_de_compra"]  # contracts
    fetched_award["award_currency"] = "Colombian Peso"
    fetched_award["buyer_name"] = entry["nombre_entidad"]  # contract
    fetched_award["source_url"] = entry["urlproceso"]["url"]  # contract
    fetched_award["entity_code"] = entry["codigo_entidad"]  # contract
    fetched_award["previous"] = False
    fetched_award["procurement_method"] = entry["modalidad_de_contratacion"]  # contract
    fetched_award["contracting_process_id"] = entry["proceso_de_compra"]  # contract
    fetched_award["procurement_category"] = entry["tipo_de_contrato"]  # contract
    fetched_award["source_data"] = entry["urlproceso"]
    fetched_award["contractperiod_enddate"] = entry["fecha_de_fin_del_contrato"]  # contract
    fetched_award["payment_method"] = (
        entry["habilita_pago_adelantado"] + " " + entry["valor_de_pago_adelantado"]
    )  # contract

    award_url = f"https://www.datos.gov.co/resource/p6dx-8zbt.json?id_del_portafolio={entry['proceso_de_compra']}"

    award_response = requests.get(award_url, headers=headers)
    award_response_json = award_response.json()[0]

    fetched_award["award_amount"] = award_response_json["valor_total_adjudicacion"]  # award
    fetched_award["title"] = award_response_json["nombre_del_procedimiento"]  # award
    fetched_award["description"] = award_response_json["nombre_del_procedimiento"]  # award
    fetched_award["award_date"] = award_response_json["fecha_adjudicacion"]  # award
    fetched_award["contractperiod_startdate"] = entry.get("fecha_de_inicio_del_contrato", None)  # award
    fetched_award["contractperiod_enddate"] = entry.get("fecha_de_fin_del_contrato", None)  # award

    fetched_award["contract_status"] = award_response_json["estado_del_procedimiento"]  # award
    fetched_award["source_last_updated_at"] = award_response_json["fecha_de_ultima_publicaci"]  # award
    fetched_award["borrower_id"] = borrower_id
    endpoint_response = requests.post(f"{backend_url}/awards/", json=fetched_award)
    print(endpoint_response.json())


for entry in response_json:
    borrower_id = complete_borrower(entry)
    fetched_award = complete_award(entry, borrower_id)
    break
