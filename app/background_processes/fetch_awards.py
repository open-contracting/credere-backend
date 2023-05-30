from datetime import datetime, time

import requests

headers = {"X-App-Token": "93JBix5v3zmG1PObXvl6iDrXk"}
today = datetime.now().date()
eight_am = time(8, 0, 0)
today_at_eight_am = datetime.combine(today, eight_am)
formatted_datetime = today_at_eight_am.strftime("%Y-%m-%dT00:00:00.000")
testing = "2023-05-29T00:00:00.000"
url = (
    "https://www.datos.gov.co/resource/jbjy-vk9h.json?$where=es_pyme = 'Si' AND estado_contrato = 'Borrador' "
    f"AND ultima_actualizacion >= '{testing}' AND localizaci_n = 'Colombia, Bogotá, Bogotá'"
)


response = requests.get(url, headers=headers)
response_json = response.json()

fetched_award = {}


for entry in response_json:
    fetched_award["proceso_de_compra"] = entry["proceso_de_compra"]  # contracts
    fetched_award["award_currency"] = "Colombian Peso"
    fetched_award["buyer_name"] = entry["nombre_entidad"]  # contract
    fetched_award["source_url"] = entry["urlproceso"]  # contract
    fetched_award["entity_code"] = entry["codigo_entidad"]  # contract
    fetched_award["previous"] = False
    fetched_award["procurement_method"] = entry["modalidad_de_contratacion"]  # contract
    fetched_award["contracting_process_id"] = entry["proceso_de_compra"]  # contract
    fetched_award["procurement_category"] = entry["tipo_de_contrato"]  # contract
    fetched_award["source_data"] = entry["urlproceso"]
    fetched_award["contractperiod_enddate"] = entry["fecha_de_fin_del_contrato"]  # contract
    fetched_award["payment_method"] = entry["habilita_pago_adelantado"] + entry["valor_de_pago_adelantado"]  # contract
    award_url = f"https://www.datos.gov.co/resource/p6dx-8zbt.json?id_del_portafolio={entry['proceso_de_compra']}"

    award_response = requests.get(award_url, headers=headers)
    award_response_json = award_response.json()[0]

    fetched_award["award_amount"] = award_response_json["valor_total_adjudicacion"]  # award
    fetched_award["title"] = award_response_json["nombre_del_procedimiento"]  # award
    fetched_award["description"] = award_response_json["nombre_del_procedimiento"]  # award
    fetched_award["award_date"] = award_response_json["fecha_adjudicacion"]  # award
    # fetched_award["contractperiod_startdate"] = award_response_json["fecha_de_inicio_del_contrato"]  # award

    fetched_award["contract_status"] = award_response_json["estado_del_procedimiento"]  # award
    fetched_award["source_last_updated_at"] = award_response_json["fecha_de_ultima_publicaci"]  # award
    endpoint_response = requests.post("http://127.0.0.1:8000/awards/", json=fetched_award)
    print(fetched_award)
    break


# award = Award(
#     source_contract_id=response["proceso_de_compra"],
#     title=response["nombre_del_procedimiento"],
#     description=response["nombre_del_procedimiento"],
#     award_date=response["fecha_adjudicacion"],
#     award_amount=response["valor_total_adjudicacion"],
#     award_currency=response["??"],
#     contractperiod_startdate=response["fecha_de_inicio_del_contrato"],
#     contractperiod_enddate=response["fecha_de_fin_del_contrato"],
#     payment_method=response[""],
#     buyer_name=response["nombre_entidad"],
#     source_url=response["urlproceso"],
#     entity_code=response["codigo_entidad"],
#     contract_status=response["estado_del_procedimiento"],
#     source_last_updated_at=response["fecha_de_ultima_publicaci"],
#     previous="Yes/No",
#     procurement_method=response["modalidad_de_contratacion endpoint anterior"],
#     contracting_process_id=response["proceso de compra endpoint anterior"],
#     procurement_category=response["tipo_de_contrato"],
#     source_data="all text in endpoint",
# )


# award_convertion_table = {
#     "source_contract_id": "proceso_de_compra",
#     "title": "nombre_del_procedimiento",
#     "description": "nombre_del_procedimiento",
#     "award_date": "fecha_adjudicacion",
#     "award_amount": "valor_total_adjudicacion",
#     "contractperiod_startdate": "fecha_de_inicio_del_contrato",
#     "contractperiod_enddate": "fecha_de_fin_del_contrato",
#     "buyer_name": "nombre_entidad",
#     "source_url": "urlproceso",
#     "entity_code": "codigo_entidad",
#     "contract_status": "estado_del_procedimiento",
#     "source_last_updated_at": "fecha_de_ultima_publicaci",
#     "procurement_method": "modalidad_de_contratacion",
#     "contracting_process_id": "proceso_de_compra",
#     "procurement_category": "tipo_de_contrato",
#     "source_data": "urlproceso",
# }
