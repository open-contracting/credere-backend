from typing import Optional

from fastapi import APIRouter, Depends, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schema import core

router = APIRouter()


class ApplicationTestPayload(BaseModel):
    status: core.ApplicationStatus
    lender_id: Optional[int]
    credit_product_id: Optional[int]


class ApplicationActionTestPayload(BaseModel):
    type: core.ApplicationActionType
    application_id: int
    user_id: int


class UpdateApplicationStatus(BaseModel):
    status: core.ApplicationStatus


class BorrowerTestPayload(BaseModel):
    status: core.BorrowerStatus


@router.post(
    "/create-test-credit-option",
    tags=["applications"],
    response_model=core.CreditProduct,
)
async def create_test_credit_option(
    payload: core.CreditProduct, session: Session = Depends(get_db)
):
    session.add(payload)
    session.commit()
    session.refresh(payload)

    return payload


@router.post("/create-test-application-action", tags=["applications"])
async def create_test_application_action(
    payload: ApplicationActionTestPayload, session: Session = Depends(get_db)
):
    update_dict = jsonable_encoder(payload, exclude_unset=True)

    new_action = core.ApplicationAction(
        type=type,
        data=update_dict,
        application_id=payload.application_id,
        user_id=payload.user_id,
    )
    session.add(new_action)
    session.flush()

    return new_action


@router.post(
    "/applications/{id}/update-test-application-status",
    tags=["applications"],
    response_model=core.Application,
)
async def update_test_application_status(
    id: int, payload: UpdateApplicationStatus, session: Session = Depends(get_db)
):
    application = (
        session.query(core.Application).filter(core.Application.id == id).first()
    )
    application.status = payload.status
    session.commit()

    return application


@router.post("/create-test-application", tags=["applications"])
async def create_test_application(
    payload: ApplicationTestPayload, session: Session = Depends(get_db)
):
    test_award = {
        "entidad": "TEST ENTITY",
        "nit_entidad": "1234567890",
        "departamento_entidad": "Test Department",
        "ciudad_entidad": "Test City",
        "ordenentidad": "Test Order",
        "codigo_pci": "Yes",
        "award_amount": "123456",
        "id_del_proceso": "TEST_PROCESS_ID",
        "referencia_del_proceso": "TEST_PROCESS_REFERENCE",
        "ppi": "ND",
        "id_del_portafolio": "TEST_PORTFOLIO_ID",
        "nombre_del_procedimiento": "Test Procedure Name",
        "descripci_n_del_procedimiento": "Test Procedure Description",
        "fase": "Test Phase",
        "fecha_de_publicacion_del": "2023-01-01T00:00:00.000",
        "fecha_de_ultima_publicaci": "2023-01-01T00:00:00.000",
        "fecha_de_publicacion_fase_3": "2023-01-01T00:00:00.000",
        "precio_base": "100000",
        "modalidad_de_contratacion": "Test Contract Modality",
        "justificaci_n_modalidad_de": "Test Modality Justification",
        "duracion": "2",
        "unidad_de_duracion": "Days",
        "fecha_de_recepcion_de": "2023-01-05T00:00:00.000",
        "fecha_de_apertura_de_respuesta": "2023-01-06T00:00:00.000",
        "fecha_de_apertura_efectiva": "2023-01-06T00:00:00.000",
        "ciudad_de_la_unidad_de": "Test Unit City",
        "nombre_de_la_unidad_de": "Test Unit Name",
        "proveedores_invitados": "3",
        "proveedores_con_invitacion": "0",
        "visualizaciones_del": "0",
        "proveedores_que_manifestaron": "0",
        "respuestas_al_procedimiento": "1",
        "respuestas_externas": "0",
        "conteo_de_respuestas_a_ofertas": "0",
        "proveedores_unicos_con": "1",
        "numero_de_lotes": "0",
        "estado_del_procedimiento": "Adjudicado",
        "id_estado_del_procedimiento": "70",
        "adjudicado": "Si",
        "id_adjudicacion": "TEST_AWARD_ID",
        "codigoproveedor": "713916229",
        "departamento_proveedor": "No aplica",
        "ciudad_proveedor": "No aplica",
        "fecha_adjudicacion": "2023-01-09T00:00:00.000",
        "valor_total_adjudicacion": "100000",
        "nombre_del_adjudicador": "Test Adjudicator",
        "nombre_del_proveedor": "Test Provider",
        "nit_del_proveedor_adjudicado": "No Definido",
        "codigo_principal_de_categoria": "V1.90101603",
        "estado_de_apertura_del_proceso": "Cerrado",
        "tipo_de_contrato": "Servicios de aprovisionamiento",
        "subtipo_de_contrato": "No Especificado",
        "categorias_adicionales": "ND",
        "urlproceso": {"url": "https://example.com"},
        "codigo_entidad": "702836172",
        "estadoresumen": "Adjudicado",
    }

    test_borrower = {
        "size": "NOT_INFORMED",
        "missing_data": {
            "borrower_identifier": False,
            "legal_name": False,
            "email": False,
            "address": False,
            "legal_identifier": True,
            "type": False,
            "source_data": False,
        },
        "updated_at": "2023-06-22T17:48:05.381251",
        "id": 1,
        "legal_name": "Test Entity",
        "address": "Direccion: Test Address\nCiudad: Test City\nProvincia: No provisto\nEstado: No provisto",
        "type": "Test Organization Type",
        "source_data": {
            "nombre_entidad": "Test Entity",
            "nit": "123456789121",
            "tel_fono_entidad": "1234567890",
            "correo_entidad": "test@example.com",
            "direccion": "Test Address",
            "estado_entidad": "Test State",
            "ciudad": "Test City",
            "website": "https://example.com",
            "tipo_organizacion": "Test Organization Type",
            "tipo_de_documento": "Test Document Type",
            "numero_de_cuenta": "Test Account Number",
            "banco": "Test Bank",
            "tipo_cuenta": "Test Account Type",
            "tipo_documento_representante_legal": "Test Representative Document Type",
            "num_documento_representante_legal": "987654321",
            "nombre_representante_legal": "Test Legal Representative",
            "nacionalidad_representante_legal": "COLOMBIANO",
            "direcci_n_representante_legal": "Test Representative Address",
            "genero_representante_legal": "No Definido",
            "es_pyme": "SI",
            "regimen_tributario": "Test Tax Regime",
            "pais": "CO",
        },
        "status": "ACTIVE",
        "created_at": "2023-06-22T17:48:06.152807",
        "declined_at": None,
        "borrower_identifier": "test_hash_12345678",
        "email": "test@example.com",
        "legal_identifier": "",
        "sector": "",
    }

    test_application = {
        "amount_requested": 10000,
        "secop_data_verification": {
            "legal_name": False,
            "address": True,
            "legal_identifier": True,
            "type": True,
            "size": True,
            "sector": True,
            "email": True,
        },
        "borrower_id": 1,
        "id": 1,
        "calculator_data": {},
        "lender_approved_at": None,
        "archived_at": None,
        "borrower_submitted_at": None,
        "lender_approved_data": {},
        "status": payload.status,
        "lender_id": payload.lender_id,
        "borrower_accepted_at": None,
        "lender_rejected_data": {},
        "award_id": 1,
        "currency": "COP",
        "borrower_declined_at": None,
        "lender_rejected_at": None,
        "uuid": "123-456-789",
        "repayment_months": None,
        "borrower_declined_preferences_data": {},
        "borrower_uploaded_contract_at": None,
        "primary_email": "test@example.com",
        "pending_documents": True,
        "contract_amount_submitted": None,
        "borrower_declined_data": {},
        "created_at": "2023-06-26T03:14:32.019854+00:00",
        "award_borrower_identifier": "test_hash_12345678",
        "pending_email_confirmation": True,
        "lender_started_at": None,
        "updated_at": "2023-06-26T03:14:31.572553+00:00",
        "completed_in_days": None,
        "credit_product_id": payload.credit_product_id,
    }

    db_award = core.Award(**test_award)

    session.add(db_award)
    session.flush()

    db_borrower = core.Borrower(**test_borrower)
    session.add(db_borrower)
    session.flush()

    db_app = core.Application(**test_application)
    session.add(db_app)
    session.commit()

    return status.HTTP_201_CREATED


@router.post("/change-test-application-status", tags=["applications"])
async def change_application_status(
    payload: ApplicationTestPayload, session: Session = Depends(get_db)
):
    application = session.query(core.Application).first()
    application.status = payload.status
    session.commit()

    return status.HTTP_200_OK


@router.post("/change-test-borrower-status", tags=["applications"])
async def change_borrower_status(
    payload: BorrowerTestPayload, session: Session = Depends(get_db)
):
    borrower = session.query(core.Borrower).first()
    borrower.status = payload.status
    session.commit()

    return status.HTTP_200_OK
