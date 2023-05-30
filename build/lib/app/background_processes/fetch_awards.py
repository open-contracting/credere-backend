from datetime import datetime, time

import requests

headers = {"X-App-Token": "93JBix5v3zmG1PObXvl6iDrXk"}


today = datetime.now().date()
eight_am = time(8, 0, 0)
today_at_eight_am = datetime.combine(today, eight_am)
formatted_datetime = today_at_eight_am.strftime("%Y-%m-%dT00:00:00.000")
testing = "2023-05-23T00:00:00.000"
url = (
    "https://www.datos.gov.co/resource/jbjy-vk9h.json?$where=es_pyme = 'Si' AND estado_contrato = 'Borrador' "
    f"AND ultima_actualizacion >= '{testing}' AND localizaci_n = 'Colombia, Bogotá, Bogotá'"
)

response = requests.get(url, headers=headers)

for entry in response.json():
    print(entry)

# response = {}

# award = Award(
#     source_contract_id=response["id_del_proceso / id_del_portafolio"],
#     title=response["nombre_del_procedimiento"],
#     description=response["nombre_del_procedimiento"],
#     award_date=response["fecha_adjudicacion"],
#     award_amount=response["valor_total_adjudicacion"],
#     award_currency=response["??"],
#     contractperiod_startdate=response[""],
#     contractperiod_enddate=response["fecha_de_inicio_del_contrato"],
#     payment_method=response["fecha_de_fin_del_contrato"],
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
