import json
import re
from datetime import datetime
from typing import Dict, List

from fastapi import File, HTTPException, UploadFile, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import asc, desc, text
from sqlalchemy.orm import Session, defaultload, joinedload

from app.background_processes.background_utils import generate_uuid
from app.schema.api import ApplicationListResponse

from ..schema import core
from .general_utils import update_models, update_models_with_validation

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
valid_email = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.(com|co)$"

excluded_applications = [
    # core.ApplicationStatus.PENDING,
    core.ApplicationStatus.REJECTED,
    core.ApplicationStatus.LAPSED,
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

valid_secop_fields = [
    "borrower_identifier",
    "legal_name",
    "email",
    "address",
    "legal_identifier",
    "type",
    "source_data",
]


def veify_data_field(application: core.Application, field: str):
    if field not in valid_secop_fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Field is not valid",
        )

    verified_data = application.secop_data_verification.copy()
    verified_data[field] = not verified_data[field]
    application.secop_data_verification = verified_data.copy()


def verify_document(document_id: int, session: Session):
    document = (
        session.query(core.BorrowerDocument)
        .filter(core.BorrowerDocument.id == document_id)
        .first()
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    document.verified = not document.verified


def allowed_file(filename):
    allowed_extensions = {"png", "pdf", "jpeg"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


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


def create_application_action(
    session: Session,
    user_id: int,
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
    print(new_action)
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
            detail="Format not allowed. It must be a PNG, JPEG, or PDG file",
        )
    new_file = file.file.read()
    if len(new_file) >= MAX_FILE_SIZE:  # 10MB in bytes
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File is too large",
        )
    return new_file, filename


def get_application_by_uuid(uuid: str, session: Session):
    application = (
        session.query(core.Application)
        .options(
            defaultload(core.Application.borrower), defaultload(core.Application.award)
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
    body: dict,
) -> None:
    obj_db = core.Message(
        application=application,
        type=message,
        external_message_id=external_message_id,
        body=json.dumps(body),
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
    application.confirmation_email_token = confirmation_email_token
    application.primary_email = email
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
    if application.confirmation_email_token != confirmation_email_token:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Not authorized to modify this application",
        )

    application.pending_email_confirmation = False
    application.confirmation_email_token = ""


def create_or_update_borrower_document(
    filename: str,
    application: core.Application,
    type: core.BorrowerDocumentType,
    session: Session,
    file: UploadFile = File(...),
):
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
    else:
        new_document = {
            "application_id": application.id,
            "type": type,
            "file": file,
            "name": filename,
        }

        db_obj = core.BorrowerDocument(**new_document)
        session.add(db_obj)


def check_FI_user_permission(application: core.Application, user: core.User) -> None:
    if application.lender_id != user.lender_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not authorized",
        )
