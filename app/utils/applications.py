import logging
import os.path
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from fastapi import File, HTTPException, UploadFile, status
from reportlab.platypus import Paragraph
from sqlalchemy.orm import Session, defaultload, joinedload

from app import models
from app.i18n import get_translated_string
from app.settings import app_settings
from reportlab_mods import styleN

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = app_settings.max_file_size_mb * 1024 * 1024  # MB in bytes
allowed_extensions = {".png", ".pdf", ".jpeg", ".jpg"}

OCP_cannot_modify = [
    models.ApplicationStatus.LAPSED,
    models.ApplicationStatus.DECLINED,
    models.ApplicationStatus.APPROVED,
    models.ApplicationStatus.CONTRACT_UPLOADED,
    models.ApplicationStatus.COMPLETED,
    models.ApplicationStatus.REJECTED,
]


document_type_keys = [doc_type.name for doc_type in models.BorrowerDocumentType]


class ERROR_CODES(Enum):
    BORROWER_FIELD_VERIFICATION_MISSING = "BORROWER_FIELD_VERIFICATION_MISSING"
    DOCUMENT_VERIFICATION_MISSING = "DOCUMENT_VERIFICATION_MISSING"
    APPLICATION_LAPSED = "APPLICATION_LAPSED"
    APPLICATION_ALREADY_COPIED = "APPLICATION_ALREADY_COPIED"


def validate_file(file: UploadFile = File(...)) -> Dict[File, str]:
    """
    Validates the uploaded file.

    This function checks whether the file has an allowed format (PNG, JPEG, or PDF) and whether its size is below
    the maximum allowed size. If the file does not pass these checks, an HTTPException is raised. Otherwise, the file
    and its filename are returned.

    :param file: The uploaded file.
    :type file: UploadFile, optional

    :return: A dictionary mapping the file to its filename.
    :rtype: Dict[File, str]

    :raise HTTPException: If the file format is not allowed or if the file size is too large.
    """
    filename = file.filename
    if os.path.splitext(filename)[1].lower() not in allowed_extensions:
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


def get_application_by_uuid(uuid: str, session: Session) -> models.Application:
    """
    Retrieve an application by its UUID from the database.

    This function queries the database to find an application that matches the given UUID.
    It raises an HTTPException if no such application is found or if the application's status is LAPSED.

    :param uuid: The UUID of the application.
    :type uuid: str

    :param session: The database session.
    :type session: Session

    :return: The application that matches the UUID.
    :rtype: models.Application

    :raise HTTPException: If no application matches the UUID or if the application's status is LAPSED.
    """
    application = (
        models.Application.filter_by(session, "uuid", uuid)
        .options(
            defaultload(models.Application.borrower),
            defaultload(models.Application.award),
            defaultload(models.Application.borrower_documents),
        )
        .first()
    )
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    if application.status == models.ApplicationStatus.LAPSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ERROR_CODES.APPLICATION_LAPSED.value,
        )

    return application


def get_application_by_id(id: int, session: Session) -> models.Application:
    """
    Retrieve an application by its ID from the database.

    This function queries the database to find an application that matches the given ID.
    It raises an HTTPException if no such application is found.

    :param id: The ID of the application.
    :type id: int

    :param session: The database session.
    :type session: Session

    :return: The application that matches the ID.
    :rtype: models.Application

    :raise HTTPException: If no application matches the ID.
    """
    application = (
        models.Application.filter_by(session, "id", id)
        .options(joinedload(models.Application.borrower), joinedload(models.Application.award))
        .first()
    )
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    return application


def get_modified_data_fields(application: models.Application, session: Session):
    application_actions = (
        session.query(models.ApplicationAction)
        .join(models.Application)
        .filter(
            models.ApplicationAction.application_id == application.id,
            models.ApplicationAction.type.in_(
                [models.ApplicationActionType.AWARD_UPDATE.value, models.ApplicationActionType.BORROWER_UPDATE.value]
            ),
        )
        .all()
    )
    modified_data_fields = {"award_updates": {}, "borrower_updates": {}}

    for action in application_actions:
        action_data = action.data
        key_prefix = (
            "award_updates" if action.type == models.ApplicationActionType.AWARD_UPDATE else "borrower_updates"
        )
        for key, value in action_data.items():
            if (
                key not in modified_data_fields[key_prefix]
                or action.created_at > modified_data_fields[key_prefix][key]["modified_at"]
            ):
                modified_data_fields[key_prefix][key] = {
                    "modified_at": action.created_at,
                    "user": action.user.name,
                    "user_type": action.user.type,
                }

    return models.ApplicationWithRelations(
        **application.dict(),
        award=application.award,
        borrower=application.borrower,
        lender=application.lender,
        credit_product=application.credit_product,
        borrower_documents=application.borrower_documents,
        modified_data_fields=modified_data_fields,
    )


def check_is_application_expired(application: models.Application):
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
    application: models.Application,
    applicationStatus: models.ApplicationStatus,
):
    """
    Check whether the application has expired.

    This function checks the expiration time of the provided application. It raises an HTTPException
    if the application has expired.

    :param application: The application to check.
    :type application: models.Application

    :raise HTTPException: If the application has expired.
    """
    if application.status != applicationStatus:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Application status is not {}".format(applicationStatus.name),
        )


def check_application_in_status(
    application: models.Application,
    applicationStatus: List[models.ApplicationStatus],
):
    """
    Check if the application's status is among a provided list of statuses.

    This function checks if the status of the given application is in a list of allowed statuses.
    If the status is not in the list, it raises an HTTPException.

    :param application: The application to check.
    :type application: models.Application

    :param applicationStatus: A list of allowed application statuses.
    :type applicationStatus: List[models.ApplicationStatus]

    :param detail: A custom error message to provide in case the status is not in the list.
                If not provided, a default error message is used.
    :type detail: str, optional

    :raise HTTPException: If the application's status is not in the provided list.
    """

    if application.status not in applicationStatus:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Application status should not be {}".format(application.status.name),
        )


def check_application_not_status(
    application: models.Application,
    applicationStatus: List[models.ApplicationStatus],
):
    """
    Check if the application's status is not among a provided list of statuses.

    This function checks if the status of the given application is not in a list of disallowed statuses.
    If the status is in the list, it raises an HTTPException.

    :param application: The application to check.
    :type application: models.Application

    :param applicationStatus: A list of disallowed application statuses.
    :type applicationStatus: List[models.ApplicationStatus]

    :param detail: A custom error message to provide in case the status is in the list.
                If not provided, a default error message is used.
    :type detail: str, optional

    :raise HTTPException: If the application's status is in the disallowed list.
    """

    if application.status in applicationStatus:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Application status is {}".format(application.status.name),
        )


def check_pending_email_confirmation(application: models.Application, confirmation_email_token: str):
    """
    Checks and processes pending email confirmation for an application.

    This function checks if the application is pending an email confirmation. If not, it raises an HTTP exception.
    It then splits the application's confirmation email token to get the new email and token.
    If the token doesn't match the provided confirmation email token, an HTTP exception is raised.
    If the tokens match, the application's primary email is updated with the new email, the application's
    pending email confirmation status is set to False, and the application's confirmation email token is reset.

    :param application: The application for which the email confirmation is to be checked and processed.
    :type application: models.Application

    :param confirmation_email_token: The confirmation email token provided for checking.
    :type confirmation_email_token: str
    """

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
    application: models.Application,
    type: models.BorrowerDocumentType,
    session: Session,
    file: UploadFile = File(...),
    verified: Optional[bool] = False,
) -> models.BorrowerDocument:
    """
    Creates a new borrower document or updates an existing one.

    This function first checks if a document of the same type already exists for the application in the session.
    If it does, it updates the existing document's file, name, verified status, and submission time with the provided values. # noqa
    If it doesn't, it creates a new BorrowerDocument with the provided values and adds it to the session.

    :param filename: The name of the file to be added or updated.
    :type filename: str

    :param application: The application associated with the document.
    :type application: models.Application

    :param type: The type of the document.
    :type type: models.BorrowerDocumentType

    :param session: The database session.
    :type session: Session

    :param file: The file to be added or updated.
    :type file: UploadFile

    :param verified: The verified status of the document. Defaults to False.
    :type verified: Optional[bool]

    :return: The newly created or updated BorrowerDocument.
    :rtype: models.BorrowerDocument
    """

    existing_document = (
        session.query(models.BorrowerDocument)
        .filter(
            models.BorrowerDocument.application_id == application.id,
            models.BorrowerDocument.type == type,
        )
        .first()
    )

    if existing_document:
        return existing_document.update(
            session,
            file=file,
            name=filename,
            verified=verified,
            submitted_at=datetime.utcnow(),
        )
    else:
        new_document = {
            "application_id": application.id,
            "type": type,
            "file": file,
            "name": filename,
            "verified": verified,
        }
        return models.BorrowerDocument.create(session, **new_document)


def check_FI_user_permission(application: models.Application, user: models.User) -> None:
    if application.lender_id != user.lender_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not authorized",
        )


def check_FI_user_permission_or_OCP(application: models.Application, user: models.User) -> None:
    """
    Checks if a user has permission to interact with a given application.

    This function checks if the lender_id associated with the application matches the lender_id of the provided user.
    If they do not match, it raises an HTTPException with a 401 status code (Unauthorized).

    :param application: The application to check.
    :type application: models.Application

    :param user: The user to check.
    :type user: models.User

    :raises HTTPException: If the lender_id of the application and user do not match.
    """

    if not user.is_OCP() and application.lender_id != user.lender_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not authorized",
        )


def create_table_cell(text: str, lang: str):
    """
    Creates a table cell for the application PDF.

    :param text: The text of the cell.
    :type text: str

    :param lang: The lang requested.
    :type lang: str

    :return: The generated cell text.
    :rtype: Paragraph
    """
    return Paragraph(get_translated_string(text, lang), styleN)
