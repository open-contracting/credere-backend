import os
from unittest.mock import patch

from fastapi import status

from app import models, util
from tests import MockResponse

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
file = os.path.join(__location__, "file.jpeg")
wrong_file = os.path.join(__location__, "file.gif")

FI_user = {
    "email": "FI_user@noreply.open-contracting.org",
    "name": "Test FI",
    "type": models.UserType.FI,
}


FI_user_with_lender = {
    "id": 2,
    "email": "FI_user_with_lender@noreply.open-contracting.org",
    "name": "Test FI with lender",
    "type": models.UserType.FI,
    "lender_id": 1,
}

FI_user_with_lender_2 = {
    "id": 3,
    "email": "FI_user_with_lender_2@noreply.open-contracting.org",
    "name": "Test FI with lender 2",
    "type": models.UserType.FI,
    "lender_id": 2,
}

OCP_user = {
    "email": "OCP_user@noreply.open-contracting.org",
    "name": "OCP_user@noreply.open-contracting.org",
    "type": models.UserType.OCP,
}

application_base = {"uuid": "123-456-789"}
application_payload = {"status": models.ApplicationStatus.PENDING}
application_with_lender_payload = {
    "status": models.ApplicationStatus.PENDING,
    "lender_id": 1,
    "credit_product_id": 1,
}
application_with_credit_product = {
    "status": models.ApplicationStatus.ACCEPTED,
    "credit_product_id": 1,
}
application_lapsed_payload = {"status": models.ApplicationStatus.LAPSED}
application_declined_payload = {"status": models.ApplicationStatus.DECLINED}
borrower_declined_oportunity_payload = {"status": models.BorrowerStatus.DECLINE_OPPORTUNITIES}
application_credit_option = {
    "uuid": "123-456-789",
    "borrower_size": models.BorrowerSize.SMALL,
    "amount_requested": 10000,
}

application_select_credit_option = {
    "uuid": "123-456-789",
    "borrower_size": models.BorrowerSize.SMALL,
    "amount_requested": 10000,
    "sector": "adminstration",
    "credit_product_id": 1,
}

lender = {
    "id": 1,
    "name": "test",
    "email_group": "test@noreply.open-contracting.org",
    "status": "Active",
    "type": "Some Type",
    "sla_days": 7,
}

lender_2 = {
    "id": 2,
    "name": "test 2",
    "email_group": "test@noreply.open-contracting.org",
    "status": "Active",
    "type": "Some Type",
    "sla_days": 7,
}
reject_payload = {
    "compliance_checks_failed": True,
    "poor_credit_history": True,
    "risk_of_fraud": False,
    "other": True,
    "other_reason": "test rejection message",
}

test_credit_option = {
    "borrower_size": "SMALL",
    "lower_limit": 5000.00,
    "upper_limit": 500000.00,
    "interest_rate": 3.75,
    "type": "LOAN",
    "required_document_types": {
        "INCORPORATION_DOCUMENT": True,
    },
    "other_fees_total_amount": 1000,
    "other_fees_description": "Other test fees",
    "more_info_url": "www.moreinfo.test",
    "lender_id": 1,
}

approve_application = {
    "compliant_checks_completed": True,
    "compliant_checks_passed": True,
    "additional_comments": "test comments",
}

update_award = {"title": "new test title"}

update_borrower = {"legal_name": "new_legal_name"}

source_award = [
    {
        "nombre_entidad": "COLEGIO GABRIEL BETANCOURT MEJIA IED",
        "nit_entidad": "900143276",
        "departamento": "Distrito Capital de Bogotá",
        "ciudad": "No Definido",
        "localizaci_n": "Colombia, Bogotá, Bogotá",
        "orden": "Territorial",
        "sector": "Educación Nacional",
        "rama": "Ejecutivo",
        "entidad_centralizada": "Descentralizada",
        "proceso_de_compra": "CO1.BDOS.4899402",
        "id_contrato": "CO1.PCCNTR.5361557",
        "referencia_del_contrato": "CO1.PCCNTR.5361557",
        "estado_contrato": "Borrador",
        "codigo_de_categoria_principal": "V1.60121200",
        "descripcion_del_proceso": "COMPRA MATERIALES PROYECTO",
        "tipo_de_contrato": "Decreto 092 de 2017",
        "modalidad_de_contratacion": "Contratación régimen especial (con ofertas)",
        "justificacion_modalidad_de": "Decreto 092 de 2017",
        "fecha_de_fin_del_contrato": "2023-09-18T00:00:00.000",
        "condiciones_de_entrega": "No Definido",
        "tipodocproveedor": "No Definido",
        "documento_proveedor": "901623692",
        "proveedor_adjudicado": "SOLUCIONES M Y T SAS",
        "es_grupo": "No",
        "es_pyme": "Si",
        "habilita_pago_adelantado": "No Definido",
        "liquidaci_n": "No",
        "obligaci_n_ambiental": "No",
        "obligaciones_postconsumo": "No",
        "reversion": "No",
        "valor_del_contrato": "3080250",
        "valor_de_pago_adelantado": "0",
        "valor_facturado": "0",
        "valor_pendiente_de_pago": "3080250",
        "valor_pagado": "0",
        "valor_amortizado": "0",
        "valor_pendiente_de": "0",
        "valor_pendiente_de_ejecucion": "3080250",
        "estado_bpin": "Válido",
        "c_digo_bpin": "No Definido",
        "anno_bpin": "N/D",
        "saldo_cdp": "0",
        "saldo_vigencia": "0",
        "espostconflicto": "No",
        "urlproceso": {"url": "https://community.secop.gov.co/Public/Tendering/OpportunityDetail"},
        "destino_gasto": "Funcionamiento",
        "origen_de_los_recursos": "Distribuido",
        "dias_adicionados": "0",
        "puntos_del_acuerdo": "No aplica",
        "pilares_del_acuerdo": "No aplica",
        "nombre_representante_legal": "TATIANA ALEJANDRA BERNAL JIMENEZ",
        "nacionalidad_representante_legal": "Colombiana",
        "tipo_de_identificaci_n_representante_legal": "Cédula de Ciudadanía",
        "identificaci_n_representante_legal": "1000375165",
        "g_nero_representante_legal": "Otro",
        "presupuesto_general_de_la_nacion_pgn": "0",
        "sistema_general_de_participaciones": "0",
        "sistema_general_de_regal_as": "0",
        "recursos_propios_alcald_as_gobernaciones_y_resguardos_ind_genas_": "4000000",
        "recursos_de_credito": "0",
        "recursos_propios": "0",
        "ultima_actualizacion": "2023-10-06T00:00:00.000",
        "codigo_entidad": "703916536",
        "codigo_proveedor": "718861537",
    }
]


def test_reject_application(client):
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    client.post("/lenders", json=lender, headers=OCP_headers)
    FI_headers = client.post("/create-test-user-headers", json=FI_user_with_lender).json()
    client.post("/create-test-credit-option", json=test_credit_option)
    client.post("/create-test-application", json=application_with_lender_payload)

    # tries to reject the application before its started
    response = client.post(
        "/applications/1/reject-application",
        json=reject_payload,
        headers=FI_headers,
    )
    assert response.status_code == status.HTTP_409_CONFLICT

    response = client.post(
        "/applications/1/update-test-application-status",
        json={"status": models.ApplicationStatus.STARTED},
    )

    response = client.post(
        "/applications/1/reject-application",
        json=reject_payload,
        headers=FI_headers,
    )
    assert response.json()["status"] == models.ApplicationStatus.REJECTED
    assert response.status_code == status.HTTP_200_OK

    response = client.post("/applications/find-alternative-credit-option", json=application_base)
    assert response.status_code == status.HTTP_200_OK


def test_rollback_credit_product(client):
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    client.post("/lenders", json=lender, headers=OCP_headers)
    client.post("/create-test-credit-option", json=test_credit_option)
    client.post("/create-test-application", json=application_with_credit_product)

    response = client.post(
        "/applications/rollback-select-credit-product",
        json=application_select_credit_option,
    )
    assert response.json()["application"]["uuid"] == application_select_credit_option["uuid"]
    assert response.json()["application"]["credit_product_id"] is None
    assert response.json()["application"]["borrower_credit_product_selected_at"] is None
    assert response.status_code == status.HTTP_200_OK


def test_access_expired_application(client):
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    client.post("/lenders", json=lender, headers=OCP_headers)
    client.post("/create-test-credit-option", json=test_credit_option)
    client.post("/create-test-application", json=application_with_credit_product)

    response = client.get("/set-application-as-expired/id/1")
    # borrower tries to access expired application
    response = client.get("/applications/uuid/123-456-789")
    assert response.status_code == status.HTTP_409_CONFLICT


def test_approve_application_cicle(client):
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    client.post("/lenders", json=lender, headers=OCP_headers)
    FI_headers = client.post("/create-test-user-headers", json=FI_user_with_lender).json()

    client.post("/lenders", json=lender_2, headers=OCP_headers)
    FI_headers_2 = client.post("/create-test-user-headers", json=FI_user_with_lender_2).json()
    client.post("/create-test-credit-option", json=test_credit_option)
    client.post("/create-test-application", json=application_with_lender_payload)

    # this will mock the previous award get to return an empty array
    with patch(
        "app.sources.colombia.get_previous_contracts",
        return_value=MockResponse(status.HTTP_200_OK, source_award),
    ):
        response = client.post("/applications/access-scheme", json=application_base)
        assert response.json()["application"]["status"] == models.ApplicationStatus.ACCEPTED
        assert response.status_code == status.HTTP_200_OK

        # Application should be accepted now so it cannot be accepted again
        response = client.post("/applications/access-scheme", json=application_base)
        assert response.status_code == status.HTTP_409_CONFLICT

    response = client.post("/applications/credit-product-options", json=application_credit_option)
    assert response.status_code == status.HTTP_200_OK

    response = client.post("/applications/select-credit-product", json=application_select_credit_option)
    assert response.status_code == status.HTTP_200_OK

    response = client.post("/applications/confirm-credit-product", json=application_base)
    assert response.status_code == status.HTTP_200_OK

    # FI user tries to fecth previous awards
    response = client.get("/applications/1/previous-awards", headers=FI_headers)
    assert len(response.json()) == len(source_award)
    assert response.json()[0]["previous"] is True
    assert response.json()[0]["entity_code"] == source_award[0]["codigo_entidad"]
    assert response.status_code == status.HTTP_200_OK

    # diffrent FI user tries to fecth previous awards
    response = client.get("/applications/1/previous-awards", headers=FI_headers_2)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # different lender tries to get the application
    response = client.get("/applications/id/1", headers=FI_headers_2)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    new_email = "new_test_email@example.com"
    new_wrong_email = "wrong_email@@noreply!$%&/().open-contracting.org"

    # borrower tries to change their email to a non valid one
    response = client.post(
        "/applications/change-email",
        json={"uuid": "123-456-789", "new_email": new_wrong_email},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    response = client.post(
        "/applications/change-email",
        json={"uuid": "123-456-789", "new_email": new_email},
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.post(
        "/applications/change-email",
        json={"uuid": "123-456-789", "new_email": new_email},
    )
    assert response.status_code == status.HTTP_200_OK

    confirmation_email_token = util.generate_uuid(new_email)

    response = client.post(
        "/applications/confirm-change-email",
        json={
            "uuid": "123-456-789",
            "confirmation_email_token": confirmation_email_token,
        },
    )
    assert response.status_code == status.HTTP_200_OK

    # borrower tries to confirm email without a pending change
    response = client.post(
        "/applications/confirm-change-email",
        json={
            "uuid": "123-456-789",
            "confirmation_email_token": "confirmation_email_token",
        },
    )
    assert response.status_code == status.HTTP_409_CONFLICT

    response = client.post("/applications/submit", json=application_base)
    assert response.json()["application"]["status"] == models.ApplicationStatus.SUBMITTED
    assert response.status_code == status.HTTP_200_OK

    # tries to upload document before application starting
    with open(file, "rb") as file_to_upload:
        response = client.post(
            "/applications/upload-document",
            data={
                "uuid": "123-456-789",
                "type": models.BorrowerDocumentType.INCORPORATION_DOCUMENT,
            },
            files={"file": (file_to_upload.name, file_to_upload, "image/jpeg")},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # different FI user tries to start the application
    response = client.post("/applications/1/start", headers=FI_headers_2)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # different FI user tries to update the award
    response = client.put("/applications/1/award", json=update_award, headers=FI_headers_2)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # different FI user tries to update the borrower
    response = client.put("/applications/1/award", json=update_borrower, headers=FI_headers_2)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # The FI user starts application
    response = client.post("/applications/1/start", headers=FI_headers)
    assert response.json()["status"] == models.ApplicationStatus.STARTED
    assert response.status_code == status.HTTP_200_OK

    # different FI user tries to update the award
    response = client.put(
        "/applications/1/award",
        json=update_award,
        headers=FI_headers_2,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN

    # different FI user tries to update the borrower
    response = client.put(
        "/applications/1/borrower",
        json=update_borrower,
        headers=FI_headers_2,
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # FI user tries to update non existing award
    response = client.put(
        "/applications/100/award",
        json=update_award,
        headers=FI_headers,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # FI user tries to update non existing borrower
    response = client.put(
        "/applications/100/borrower",
        json=update_borrower,
        headers=FI_headers,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # FI user tries to update the award
    response = client.put(
        "/applications/1/award",
        json=update_award,
        headers=FI_headers,
    )
    assert response.json()["award"]["title"] == update_award["title"]
    assert response.status_code == status.HTTP_200_OK

    # FI user tries to update the borrower
    response = client.put(
        "/applications/1/borrower",
        json=update_borrower,
        headers=FI_headers,
    )
    assert response.json()["borrower"]["legal_name"] == update_borrower["legal_name"]
    assert response.status_code == status.HTTP_200_OK

    response = client.post(
        "applications/email-sme/1",
        json={"message": "test message"},
        headers=FI_headers,
    )

    assert response.json()["status"] == models.ApplicationStatus.INFORMATION_REQUESTED
    assert response.status_code == status.HTTP_200_OK

    # borrower uploads the wrong type of document
    with open(wrong_file, "rb") as file_to_upload:
        response = client.post(
            "/applications/upload-document",
            data={
                "uuid": "123-456-789",
                "type": models.BorrowerDocumentType.INCORPORATION_DOCUMENT,
            },
            files={"file": (file_to_upload.name, file_to_upload, "image/jpeg")},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    with open(file, "rb") as file_to_upload:
        response = client.post(
            "/applications/upload-document",
            data={
                "uuid": "123-456-789",
                "type": models.BorrowerDocumentType.INCORPORATION_DOCUMENT,
            },
            files={"file": (file_to_upload.name, file_to_upload, "image/jpeg")},
        )
        assert response.status_code == status.HTTP_200_OK

        response = client.post("/applications/complete-information-request", json={"uuid": "123-456-789"})
        assert response.json()["application"]["status"] == models.ApplicationStatus.STARTED
        assert response.status_code == status.HTTP_200_OK

        response = client.get("/applications/documents/id/1", headers=FI_headers)
        assert response.status_code == status.HTTP_200_OK

        # OCP user downloads the document
        response = client.get("/applications/documents/id/1", headers=OCP_headers)
        assert response.status_code == status.HTTP_200_OK

        # OCP ask for a file that does not exist
        response = client.get("/applications/documents/id/100", headers=OCP_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # lender tries to approve the application without verifying legal_name
    response = client.post(
        "/applications/1/approve-application",
        json=approve_application,
        headers=FI_headers,
    )
    assert response.status_code == status.HTTP_409_CONFLICT

    # verify legal_name
    response = client.put(
        "/applications/1/verify-data-field",
        json={"legal_name": True},
        headers=FI_headers,
    )
    assert response.json()["secop_data_verification"] == {"legal_name": True}
    assert response.status_code == status.HTTP_200_OK

    # lender tries to approve the application without verifying INCORPORATION_DOCUMENT
    response = client.post(
        "/applications/1/approve-application",
        json=approve_application,
        headers=FI_headers,
    )
    assert response.status_code == status.HTTP_409_CONFLICT

    # verify borrower document
    response = client.put(
        "/applications/documents/1/verify-document",
        json={"verified": True},
        headers=FI_headers,
    )
    assert response.json()["verified"] is True
    assert response.status_code == status.HTTP_200_OK

    # lender approves application
    response = client.post(
        "/applications/1/approve-application",
        json=approve_application,
        headers=FI_headers,
    )
    assert response.json()["status"] == models.ApplicationStatus.APPROVED
    assert response.status_code == status.HTTP_200_OK

    # msme uploads contract
    with open(file, "rb") as file_to_upload:
        response = client.post(
            "/applications/upload-contract",
            data={"uuid": "123-456-789"},
            files={"file": (file_to_upload.name, file_to_upload, "image/jpeg")},
        )
        assert response.status_code == status.HTTP_200_OK

    response = client.post(
        "/applications/confirm-upload-contract",
        json={"uuid": "123-456-789", "contract_amount_submitted": 100000},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["application"]["status"] == models.ApplicationStatus.CONTRACT_UPLOADED

    response = client.post(
        "/applications/1/complete-application",
        json={"disbursed_final_amount": 10000},
        headers=FI_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == models.ApplicationStatus.COMPLETED


def test_get_applications(client):
    OCP_headers = client.post("/create-test-user-headers", json=OCP_user).json()
    client.post("/lenders", json=lender, headers=OCP_headers)
    FI_headers = client.post("/create-test-user-headers", json=FI_user_with_lender).json()

    client.post("/create-test-credit-option", json=test_credit_option)
    client.post("/create-test-application", json=application_with_lender_payload)

    response = client.get(
        "/applications/admin-list/?page=1&page_size=4&sort_field=borrower.legal_name&sort_order=asc",
        headers=OCP_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/applications/admin-list/?page=1&page_size=4&sort_field=borrower.legal_name&sort_order=asc")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    response = client.get("/applications/id/1", headers=OCP_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/applications/id/1", headers=FI_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/applications/id/1")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # tries to get a non existing application
    response = client.get("/applications/id/100", headers=FI_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND

    response = client.get("/applications", headers=FI_headers)
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/applications")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    response = client.get("/applications/uuid/123-456-789")
    assert response.status_code == status.HTTP_200_OK

    client.post("/change-test-application-status", json=application_lapsed_payload)
    response = client.get("/applications/uuid/123-456-789")
    assert response.status_code == status.HTTP_409_CONFLICT

    response = client.get("/applications/uuid/123-456")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    response = client.post("/applications/access-scheme", json={"uuid": "123-456"})
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_application_declined(client):
    client.post("/create-test-application", json=application_payload)

    response = client.post(
        "/applications/decline",
        json={"uuid": "123-456-789", "decline_this": False, "decline_all": True},
    )
    assert response.json()["application"]["status"] == models.ApplicationStatus.DECLINED
    assert response.json()["borrower"]["status"] == models.BorrowerStatus.DECLINE_OPPORTUNITIES
    assert response.status_code == status.HTTP_200_OK

    response = client.post("/applications/access-scheme", json={"uuid": "123-456-789"})
    assert response.status_code == status.HTTP_409_CONFLICT


def test_application_rollback_declined(client):
    client.post("/create-test-application", json=application_declined_payload)
    client.post("/change-test-borrower-status", json=borrower_declined_oportunity_payload)

    response = client.post("/applications/rollback-decline", json={"uuid": "123-456-789"})

    assert response.json()["application"]["status"] == models.ApplicationStatus.PENDING
    assert response.json()["borrower"]["status"] == models.BorrowerStatus.ACTIVE
    assert response.status_code == status.HTTP_200_OK

    response = client.post("/applications/rollback-decline", json={"uuid": "123-456-789"})
    assert response.status_code == status.HTTP_409_CONFLICT


def test_application_declined_feedback(client):
    client.post(
        "/create-test-application",
        json={"status": models.ApplicationStatus.DECLINED},
    )

    declined_feedback = {
        "uuid": "123-456-789",
        "dont_need_access_credit": True,
        "already_have_acredit": False,
        "preffer_to_go_to_bank": False,
        "dont_want_access_credit": False,
        "other": False,
        "other_comments": "comments",
    }

    response = client.post("/applications/decline-feedback", json=declined_feedback)
    assert response.json()["application"]["status"] == models.ApplicationStatus.DECLINED
    assert response.status_code == status.HTTP_200_OK
