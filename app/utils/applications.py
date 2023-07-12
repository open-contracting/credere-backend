import logging
import re
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from fastapi import File, HTTPException, UploadFile, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import asc, desc, text
from sqlalchemy.orm import Session, defaultload, joinedload

from app.background_processes.background_utils import generate_uuid
from app.core.settings import app_settings
from app.schema.api import ApplicationListResponse, UpdateDataField

from ..schema import api, core
from .general_utils import update_models, update_models_with_validation

MAX_FILE_SIZE = app_settings.max_file_size_mb * 1024 * 1024  # MB in bytes
valid_email = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.(com|co)$"

excluded_applications = [
    core.ApplicationStatus.PENDING,
    core.ApplicationStatus.ACCEPTED,
    core.ApplicationStatus.DECLINED,
]

OCP_cannot_modify = [
    core.ApplicationStatus.LAPSED,
    core.ApplicationStatus.DECLINED,
    core.ApplicationStatus.APPROVED,
    core.ApplicationStatus.CONTRACT_UPLOADED,
    core.ApplicationStatus.COMPLETED,
    core.ApplicationStatus.REJECTED,
]


document_type_keys = [doc_type.name for doc_type in core.BorrowerDocumentType]


def update_data_field(application: core.Application, payload: UpdateDataField):
    payload_dict = {
        key: value for key, value in payload.dict().items() if value is not None
    }

    key, value = next(iter(payload_dict.items()), (None, None))
    verified_data = application.secop_data_verification.copy()
    verified_data[key] = value
    application.secop_data_verification = verified_data.copy()


def allowed_file(filename):
    allowed_extensions = {"png", "pdf", "jpeg", "jpg"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def validate_fields(application):
    not_validated_fields = []
    app_secop_dict = application.secop_data_verification.copy()

    fields = list(UpdateDataField().dict().keys())

    for key in fields:
        if key not in app_secop_dict or not app_secop_dict[key]:
            not_validated_fields.append(key)
    if not_validated_fields:
        logging.error(f"Following fields were not validated: {not_validated_fields}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=api.ERROR_CODES.BORROWER_FIELD_VERIFICATION_MISSING.value,
        )


def validate_documents(application):
    not_validated_documents = []

    for document in application.borrower_documents:
        if not document.verified:
            not_validated_documents.append(document.type.name)

    if not_validated_documents:
        logging.error(
            f"Following documents were not validated: {not_validated_documents}"
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=api.ERROR_CODES.DOCUMENT_VERIFICATION_MISSING.value,
        )


def get_file(document: core.BorrowerDocument, user: core.User, session: Session):
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    if user.is_OCP():
        create_application_action(
            session,
            None,
            document.application.id,
            core.ApplicationActionType.OCP_DOWNLOAD_DOCUMENT,
            {"file_name": document.name},
        )
    else:
        check_FI_user_permission(document.application, user)
        create_application_action(
            session,
            None,
            document.application.id,
            core.ApplicationActionType.FI_DOWNLOAD_DOCUMENT,
            {"file_name": document.name},
        )


def get_calculator_data(payload: dict):
    calculator_fields = jsonable_encoder(payload, exclude_unset=True)
    calculator_fields.pop("uuid")
    calculator_fields.pop("credit_product_id")
    calculator_fields.pop("sector")

    return calculator_fields


def reject_application(application: core.Application, payload: dict):
    payload_dict = jsonable_encoder(payload, exclude_unset=True)

    application.lender_rejected_data = payload_dict
    current_time = datetime.now(application.created_at.tzinfo)
    application.lender_rejected_at = current_time
    application.status = core.ApplicationStatus.REJECTED


def approve_application(application: core.Application, payload: dict):
    validate_fields(application)
    validate_documents(application)

    payload_dict = jsonable_encoder(payload, exclude_unset=True)
    application.lender_approved_data = payload_dict
    application.status = core.ApplicationStatus.APPROVED
    current_time = datetime.now(application.created_at.tzinfo)
    application.lender_approved_at = current_time


def complete_application(
    application: core.Application, disbursed_final_amount: Decimal
):
    current_time = datetime.now(application.created_at.tzinfo)
    application.disbursed_final_amount = disbursed_final_amount
    application.status = core.ApplicationStatus.COMPLETED
    application.lender_completed_at = current_time


def create_application_action(
    session: Session,
    user_id: Optional[int],
    application_id: int,
    type: core.ApplicationAction,
    payload: dict,
) -> core.ApplicationAction:
    update_dict = jsonable_encoder(payload, exclude_unset=True)

    new_action = core.ApplicationAction(
        type=type,
        data=update_dict,
        application_id=application_id,
        user_id=user_id,
    )
    session.add(new_action)
    session.flush()

    return new_action


def update_application_borrower(
    session: Session, application_id: int, payload: dict, user: core.User
) -> core.Application:
    application = (
        session.query(core.Application)
        .filter(core.Application.id == application_id)
        .options(defaultload(core.Application.borrower))
        .first()
    )
    if not application or not application.borrower:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application or borrower not found",
        )

    check_application_not_status(
        application,
        OCP_cannot_modify,
    )

    if not user.is_OCP() and application.lender_id != user.lender_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This application is not owned by this lender",
        )

    update_models(payload, application.borrower)

    session.add(application)
    session.flush()

    return application


def update_application_award(
    session: Session, application_id: int, payload: dict, user: core.User
) -> core.Application:
    application = (
        session.query(core.Application)
        .filter(core.Application.id == application_id)
        .options(defaultload(core.Application.award))
        .first()
    )
    if not application or not application.award:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application or award not found",
        )

    check_application_not_status(
        application,
        OCP_cannot_modify,
    )

    if not user.is_OCP() and application.lender_id != user.lender_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This application is not owned by this lender",
        )

    update_models_with_validation(payload, application.award)

    session.add(application)
    session.flush()

    return application


def get_all_active_applications(
    page: int, page_size: int, sort_field: str, sort_order: str, session: Session
) -> ApplicationListResponse:
    sort_direction = desc if sort_order.lower() == "desc" else asc

    applications_query = (
        session.query(core.Application)
        .join(core.Award)
        .join(core.Borrower)
        .options(
            joinedload(core.Application.award),
            joinedload(core.Application.borrower),
        )
        .filter(core.Application.status.notin_(excluded_applications))
        .order_by(text(f"{sort_field} {sort_direction.__name__}"))
    )

    total_count = applications_query.count()

    applications = applications_query.offset(page * page_size).limit(page_size).all()

    return ApplicationListResponse(
        items=applications,
        count=total_count,
        page=page,
        page_size=page_size,
    )


def get_all_FI_user_applications(
    page: int,
    page_size: int,
    sort_field: str,
    sort_order: str,
    session: Session,
    lender_id,
) -> ApplicationListResponse:
    sort_direction = desc if sort_order.lower() == "desc" else asc

    applications_query = (
        session.query(core.Application)
        .join(core.Award)
        .join(core.Borrower)
        .options(
            joinedload(core.Application.award),
            joinedload(core.Application.borrower),
        )
        .filter(
            core.Application.status.notin_(excluded_applications),
            core.Application.lender_id == lender_id,
            core.Application.lender_id.is_not(None),
        )
        .order_by(text(f"{sort_field} {sort_direction.__name__}"))
    )
    total_count = applications_query.count()

    applications = applications_query.offset(page * page_size).limit(page_size).all()

    return ApplicationListResponse(
        items=applications,
        count=total_count,
        page=page,
        page_size=page_size,
    )


def validate_file(file: UploadFile = File(...)) -> Dict[File, str]:
    filename = file.filename
    if not allowed_file(file.filename):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Format not allowed. It must be a PNG, JPEG, or PDF file",
        )
    new_file = file.file.read()
    if len(new_file) >= MAX_FILE_SIZE:  # 10MB in bytes
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File is too large",
        )
    return new_file, filename


def get_application_by_uuid(uuid: str, session: Session) -> core.Application:
    application = (
        session.query(core.Application)
        .options(
            defaultload(core.Application.borrower),
            defaultload(core.Application.award),
            defaultload(core.Application.borrower_documents),
        )
        .filter(core.Application.uuid == uuid)
        .first()
    )

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
        )

    return application


def get_application_by_id(id: int, session: Session) -> core.Application:
    application = (
        session.query(core.Application)
        .options(
            defaultload(core.Application.borrower), defaultload(core.Application.award)
        )
        .filter(core.Application.id == id)
        .first()
    )

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
        )

    return application


def check_is_application_expired(application: core.Application):
    expired_at = application.expired_at

    if not expired_at:
        return

    current_time = datetime.now(expired_at.tzinfo)

    if application.expired_at < current_time:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Application expired",
        )


def check_application_status(
    application: core.Application,
    applicationStatus: core.ApplicationStatus,
    detail: str = None,
):
    if application.status != applicationStatus:
        message = "Application status is not {}".format(applicationStatus.name)
        if detail:
            message = detail
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
        )


def check_application_in_status(
    application: core.Application,
    applicationStatus: List[core.ApplicationStatus],
    detail: str = None,
):
    if application.status not in applicationStatus:
        message = "Application status should not be {}".format(application.status.name)
        if detail:
            message = detail
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
        )


def check_application_not_status(
    application: core.Application,
    applicationStatus: List[core.ApplicationStatus],
    detail: str = None,
):
    if application.status in applicationStatus:
        message = "Application status is {}".format(application.status.name)
        if detail:
            message = detail
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
        )


def create_message(
    application: core.Application,
    message: core.MessageType,
    session: Session,
    external_message_id: str,
) -> None:
    obj_db = core.Message(
        application=application,
        type=message,
        external_message_id=external_message_id,
    )
    obj_db.created_at = datetime.utcnow()

    session.add(obj_db)
    session.flush()


def update_application_primary_email(application: core.Application, email: str) -> str:
    if not re.match(valid_email, email):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New email is not valid",
        )
    confirmation_email_token = generate_uuid(email)
    application.confirmation_email_token = f"{email}---{confirmation_email_token}"

    application.pending_email_confirmation = True

    return confirmation_email_token


def check_pending_email_confirmation(
    application: core.Application, confirmation_email_token: str
):
    if not application.pending_email_confirmation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Application is not pending an email confirmation",
        )
    new_email = application.confirmation_email_token.split("---")[0]
    token = application.confirmation_email_token.split("---")[1]
    if token != confirmation_email_token:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Not authorized to modify this application",
        )
    application.primary_email = new_email
    application.pending_email_confirmation = False
    application.confirmation_email_token = ""


def create_or_update_borrower_document(
    filename: str,
    application: core.Application,
    type: core.BorrowerDocumentType,
    session: Session,
    file: UploadFile = File(...),
    verified: Optional[bool] = False,
) -> core.BorrowerDocument:
    existing_document = (
        session.query(core.BorrowerDocument)
        .filter(
            core.BorrowerDocument.application_id == application.id,
            core.BorrowerDocument.type == type,
        )
        .first()
    )

    if existing_document:
        # Update the existing document with the new file
        existing_document.file = file
        existing_document.name = filename
        existing_document.verified = verified
        existing_document.submitted_at = datetime.utcnow()
        return existing_document
    else:
        new_document = {
            "application_id": application.id,
            "type": type,
            "file": file,
            "name": filename,
            "verified": verified,
        }

        db_obj = core.BorrowerDocument(**new_document)
        session.add(db_obj)
        return db_obj


def check_FI_user_permission(application: core.Application, user: core.User) -> None:
    if application.lender_id != user.lender_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not authorized",
        )


def get_document_by_id(document_id: int, session: Session) -> core.BorrowerDocument:
    document = (
        session.query(core.BorrowerDocument)
        .filter(core.BorrowerDocument.id == document_id)
        .first()
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return document


def copy_documents(application: core.Application, documents: dict, session: Session):
    for document in documents:
        data = {
            "application_id": application.id,
            "type": document.type,
            "name": document.name,
            "file": document.file,
            "verified": False,
        }
        new_borrower_document = core.BorrowerDocument(**data)
        session.add(new_borrower_document)
        session.flush()
        application.borrower_documents.append(new_borrower_document)


def copy_application(
    application: core.Application, session: Session
) -> core.Application:
    try:
        data = {
            "award_id": application.award_id,
            "uuid": generate_uuid(application.uuid),
            "primary_email": application.primary_email,
            "status": core.ApplicationStatus.ACCEPTED,
            "award_borrower_identifier": application.award_borrower_identifier,
            "borrower_id": application.borrower.id,
            "borrower_accepted_at": datetime.now(application.created_at.tzinfo),
        }
        new_application = core.Application(**data)
        session.add(new_application)
        session.flush()
        return new_application

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"There was a problem copying the application.{e}",
        )


def get_previous_lenders(award_borrower_identifier: str, session: Session) -> List[int]:
    lender_ids = (
        session.query(core.Application.lender_id)
        .filter(core.Application.award_borrower_identifier == award_borrower_identifier)
        .filter(core.Application.status == "REJECTED")
        .distinct()
        .all()
    )
    if not lender_ids:
        return []
    cleaned_lender_ids = [
        lender_id for (lender_id,) in lender_ids if lender_id is not None
    ]

    return cleaned_lender_ids


def get_previous_documents(application: core.Application, session: Session):
    document_types = application.credit_product.required_document_types
    document_types_list = [key for key, value in document_types.items() if value]

    lastest_application_id = (
        session.query(core.Application.id)
        .filter(
            core.Application.status == "REJECTED",
            core.Application.award_borrower_identifier
            == application.award_borrower_identifier,
        )
        .order_by(core.Application.created_at.desc())
        .first()
    )
    if not lastest_application_id:
        return

    documents = (
        session.query(core.BorrowerDocument)
        .filter(
            core.BorrowerDocument.application_id == lastest_application_id[0],
            core.BorrowerDocument.type.in_(document_types_list),
        )
        .all()
    )

    copy_documents(application, documents, session)
