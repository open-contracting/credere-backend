import logging
import os
from datetime import datetime, timedelta
from typing import Any, Generator

import boto3
import pytest
from botocore.config import Config
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from moto import mock_cognitoidp, mock_ses
from sqlalchemy import Enum, create_engine
from sqlalchemy.orm import sessionmaker

from app.core.settings import app_settings
from app.core.user_dependencies import CognitoClient, get_cognito_client
from app.db.session import get_db
from app.email_templates import NEW_USER_TEMPLATE_NAME
from app.routers import applications, lenders, security, users
from app.schema import core

application_status_values = (
    "PENDING",
    "ACCEPTED",
    "LAPSED",
    "DECLINED",
    "SUBMITTED",
    "STARTED",
    "APPROVED",
    "CONTRACT_UPLOADED",
    "COMPLETED",
    "REJECTED",
    "INFORMATION_REQUESTED",
)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", app_settings.test_database_url)
engine = create_engine(SQLALCHEMY_DATABASE_URL)
existing_enum_types = engine.execute(
    "SELECT typname FROM pg_type WHERE typtype = 'e'"
).fetchall()
enum_exists = ("application_status",) in existing_enum_types
ApplicationStatusEnum = Enum(
    *application_status_values, name="application_status", create_type=False
)

if not enum_exists:
    engine.execute(
        "CREATE TYPE application_status AS ENUM %s" % str(application_status_values)
    )


SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    handlers=[logging.StreamHandler()],  # Output logs to the console
)


def start_application():
    app = FastAPI()
    app.include_router(users.router)
    app.include_router(lenders.router)
    app.include_router(security.router)
    app.include_router(applications.router)
    return app


@pytest.fixture(scope="function")
def app() -> Generator[FastAPI, Any, None]:
    logging.info("Creating test database")
    core.User.metadata.create_all(engine)  # Create the tables.
    _app = start_application()
    yield _app
    core.User.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def mock_cognito_client():
    with mock_cognitoidp():
        yield


@pytest.fixture(autouse=True)
def mock_ses_client():
    with mock_ses():
        yield


tempPassword = "1234567890Abc!!"

FI_user = {
    "email": "FI_user@example.com",
    "name": "Test User",
    "external_id": "123-456-789",
    "type": core.UserType.FI.value,
}

OCP_user = {
    "email": "OCP@example.com",
    "name": "Test User",
    "external_id": "123-456-789",
    "type": core.UserType.OCP.value,
}


def create_test_user(client: Generator[TestClient, Any, None], user_data: dict):
    responseCreate = client.post("/users", json=user_data)
    assert responseCreate.status_code == status.HTTP_200_OK

    setupPasswordPayload = {
        "username": user_data["email"],
        "temp_password": tempPassword,
        "password": tempPassword,
    }
    client.put("/users/change-password", json=setupPasswordPayload)

    loginPayload = {"username": user_data["email"], "password": tempPassword}
    responseLogin = client.post("/users/login", json=loginPayload)

    return {"Authorization": "Bearer " + responseLogin.json()["access_token"]}


def create_application(
    status: core.ApplicationStatus = core.ApplicationStatus.PENDING,
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
        "amount_requested": None,
        "secop_data_verification": {},
        "borrower_id": 1,
        "id": 1,
        "calculator_data": {},
        "lender_approved_at": None,
        "archived_at": None,
        "borrower_submitted_at": None,
        "lender_approved_data": {},
        "status": status.value,
        "lender_id": None,
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
    }

    connection = engine.connect()
    with SessionTesting(bind=connection) as session:
        db_award = core.Award(**test_award)

        session.add(db_award)
        session.flush()

        db_borrower = core.Borrower(**test_borrower)
        session.add(db_borrower)
        session.flush()

        db_app = core.Application(**test_application)
        session.add(db_app)
        session.commit()


def set_application_as_expired():
    connection = engine.connect()
    with SessionTesting(bind=connection) as session:
        db_app = session.query(core.Application).first()
        db_app.expired_at = datetime.now() - timedelta(hours=1)
        session.add(db_app)
        session.commit()


def set_application_status(status: core.ApplicationStatus):
    connection = engine.connect()
    with SessionTesting(bind=connection) as session:
        db_obj = session.query(core.Application).first()
        db_obj.status = status
        session.add(db_obj)
        session.commit()


def set_borrower_status(status: core.BorrowerStatus):
    connection = engine.connect()
    with SessionTesting(bind=connection) as session:
        db_obj = session.query(core.Borrower).first()
        db_obj.status = status
        session.add(db_obj)
        session.commit()


@pytest.fixture(scope="function")
def client(app: FastAPI) -> Generator[TestClient, Any, None]:
    my_config = Config(region_name=app_settings.aws_region)

    cognito_client = boto3.client("cognito-idp", config=my_config)
    ses_client = boto3.client("ses", config=my_config)

    cognito_pool_id = cognito_client.create_user_pool(PoolName="TestUserPool")[
        "UserPool"
    ]["Id"]

    app_settings.cognito_pool_id = cognito_pool_id

    cognito_client_name = "TestAppClient"

    cognito_client_id = cognito_client.create_user_pool_client(
        UserPoolId=cognito_pool_id, ClientName=cognito_client_name
    )["UserPoolClient"]["ClientId"]

    app_settings.cognito_client_id = cognito_client_id
    app_settings.cognito_client_secret = "secret"

    ses_client.verify_email_identity(EmailAddress=app_settings.email_sender_address)

    ses_client.create_template(
        Template={
            "TemplateName": NEW_USER_TEMPLATE_NAME,
            "SubjectPart": "Your email subject",
            "HtmlPart": "<html><body>Your HTML content</body></html>",
            "TextPart": "Your plain text content",
        }
    )

    def generate_test_password():
        logging.info("generate_password")
        return tempPassword

    def _get_test_cognito_client():
        try:
            yield CognitoClient(
                cognito_client,
                ses_client,
                generate_test_password,
            )
        finally:
            pass

    connection = engine.connect()
    session = SessionTesting(bind=connection)

    def _get_test_db():
        try:
            yield session
        finally:
            session.close()

    # Override the clients dependencies with the mock implementations
    app.dependency_overrides[get_cognito_client] = _get_test_cognito_client
    app.dependency_overrides[get_db] = _get_test_db

    with TestClient(app) as client:
        yield client
        connection.close()
