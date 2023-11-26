import logging
import os.path
import re
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from fastapi import File, HTTPException, UploadFile, status
from fastapi.encoders import jsonable_encoder
from reportlab.platypus import Paragraph
from sqlalchemy import asc, desc, text
from sqlalchemy.orm import Session, defaultload, joinedload

from app import models, parsers, serializers, util
from app.i18n import get_translated_string
from app.settings import app_settings
from reportlab_mods import styleN

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = app_settings.max_file_size_mb * 1024 * 1024  # MB in bytes
valid_email = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
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


def update_data_field(application: models.Application, payload: parsers.UpdateDataField):
    """
    Update a specific field in the application's `secop_data_verification` attribute.

    :param application: The application to update.
    :type application: models.Application

    :param payload: The data to be updated.
    :type payload: parsers.UpdateDataField

    :raise: KeyError if the key specified in payload does not exist in the application's secop_data_verification dictionary. # noqa

    """
    payload_dict = {key: value for key, value in payload.dict().items() if value is not None}
    key, value = next(iter(payload_dict.items()), (None, None))
    verified_data = application.secop_data_verification.copy()
    verified_data[key] = value
    application.secop_data_verification = verified_data.copy()


def validate_fields(application):
    """
    Validates the fields in an application's `secop_data_verification` attribute.

    This function checks if all keys present in an instance of UpdateDataField exist and have truthy values in
    the application's `secop_data_verification`. If any such keys are not present or have falsy values,
    it logs an error and raises an HTTPException.

    :param application: The application to validate.
    :type application: models.Application

    :raise HTTPException: Raises an exception with status code 409 and a BORROWER_FIELD_VERIFICATION_MISSING error detail if any field is not validated. # noqa

    """
    not_validated_fields = []
    app_secop_dict = application.secop_data_verification.copy()

    fields = list(parsers.UpdateDataField().dict().keys())

    for key in fields:
        if key not in app_secop_dict or not app_secop_dict[key]:
            not_validated_fields.append(key)
    if not_validated_fields:
        logger.error(f"Following fields were not validated: {not_validated_fields}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ERROR_CODES.BORROWER_FIELD_VERIFICATION_MISSING.value,
        )


def validate_documents(application):
    """
    Validates the documents attached to an application.

    This function iterates over the borrower_documents in an application. If any document is not verified,
    it logs an error and raises an HTTPException.

    :param application: The application whose documents are to be validated.
    :type application: models.Application

    :raise HTTPException: Raises an exception with status code 409 and a DOCUMENT_VERIFICATION_MISSING error detail if any document is not validated.# noqa
    """
    not_validated_documents = []

    for document in application.borrower_documents:
        if not document.verified:
            not_validated_documents.append(document.type.name)

    if not_validated_documents:
        logger.error(f"Following documents were not validated: {not_validated_documents}")

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ERROR_CODES.DOCUMENT_VERIFICATION_MISSING.value,
        )


def get_file(document: models.BorrowerDocument, user: models.User, session: Session):
    """
    Fetches a file corresponding to a document of an application.

    This function raises an HTTPException if the document is not found. If the user is an OCP, it creates an
    application action of type OCP_DOWNLOAD_DOCUMENT. If the user is an FI, it checks the user's permissions
    and then creates an application action of type FI_DOWNLOAD_DOCUMENT.

    :param document: The document associated with the file to be fetched.
    :type document: models.BorrowerDocument

    :param user: The user trying to fetch the file.
    :type user: models.User

    :param session: The database session.
    :type session: Session

    :raise HTTPException: Raises an exception with status code 404 and a "Document not found" error detail if the document does not exist. # noqa

    :raise HTTPException: Raises an exception with status code 403 if the FI user does not have sufficient permissions to fetch the file (this is implied by the call to check_FI_user_permission). # noqa

    """
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    if user.is_OCP():
        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.OCP_DOWNLOAD_DOCUMENT,
            data={"file_name": document.name},
            application_id=document.application.id,
        )
    else:
        check_FI_user_permission(document.application, user)
        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.FI_DOWNLOAD_DOCUMENT,
            data={"file_name": document.name},
            application_id=document.application.id,
        )


def get_calculator_data(payload: dict):
    """
    Extracts the necessary fields for a calculator from a payload.

    This function encodes the payload into JSON, removes unset fields, and then removes the "uuid",
    "credit_product_id", and "sector" fields. The remaining fields are returned.

    :param payload: The input data payload.
    :type payload: dict

    :return: A dictionary containing the fields necessary for a calculator.
    :rtype: dict
    """
    calculator_fields = jsonable_encoder(payload, exclude_unset=True)
    calculator_fields.pop("uuid")
    calculator_fields.pop("credit_product_id")
    calculator_fields.pop("sector")

    return calculator_fields


def approve_application(application: models.Application, payload: dict):
    """
    Approves an application.

    This function validates the fields and documents of the application, encodes a payload into JSON,
    removes unset fields, sets these fields as the `lender_approved_data` in the application,
    changes the application status to APPROVED, and updates the `lender_approved_at` timestamp.

    :param application: The application to be approved.
    :type application: models.Application

    :param payload: The data payload associated with the approval.
    :type payload: dict

    :raise HTTPException: Raises an exception if any field or document is not validated (implied by the calls to validate_fields and validate_documents).# noqa
    """

    validate_fields(application)
    validate_documents(application)

    payload_dict = jsonable_encoder(payload, exclude_unset=True)
    application.lender_approved_data = payload_dict
    application.status = models.ApplicationStatus.APPROVED
    current_time = datetime.now(application.created_at.tzinfo)
    application.lender_approved_at = current_time


def update_application_borrower(
    session: Session, application_id: int, payload: dict, user: models.User
) -> models.Application:
    """
    Updates the borrower of an application.

    This function fetches an application and its associated borrower from the database. If the application or
    the borrower is not found, it raises an HTTPException. It checks if the application status is not in the
    OCP_cannot_modify list. If the user is not an OCP and does not own the application, it raises an HTTPException.
    Then it updates the borrower model with the provided payload. The application is added back to the session
    and then returned.

    :param session: The database session.
    :type session: Session

    :param application_id: The ID of the application associated with the borrower to be updated.
    :type application_id: int

    :param payload: The data payload for updating the borrower.
    :type payload: dict

    :param user: The user trying to update the borrower.
    :type user: models.User

    :return: The updated Application.
    :rtype: models.Application

    :raise HTTPException: Raises an exception with status code 404 and a "Application or borrower not found" error detail if the application or borrower does not exist.# noqa

    :raise HTTPException: Raises an exception with status code 403 and a "This application is not owned by this lender" error detail if the user is not an OCP and does not own the application.# noqa

    :raise HTTPException: Raises an exception if the application status is in the OCP_cannot_modify list (implied by the call to check_application_not_status). # noqa
    """
    application = (
        models.Application.filter_by(session, "id", application_id)
        .options(defaultload(models.Application.borrower))
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

    # Update the borrower, but return the application.
    update_dict = jsonable_encoder(payload, exclude_unset=True)
    for field, value in update_dict.items():
        if not application.borrower.missing_data[field]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="This column cannot be updated",
            )
    application.borrower.update(session, **update_dict)

    return application


def update_application_award(
    session: Session, application_id: int, payload: dict, user: models.User
) -> models.Application:
    """
    Updates the award of an application.

    This function fetches an application and its associated award from the database. If the application or
    the award is not found, it raises an HTTPException. It checks if the application status is not in the
    'OCP_cannot_modify' list. If the user is not an OCP and does not own the application, it raises an
    HTTPException.

    :param session: The database session.
    :type session: Session

    :param application_id: The ID of the application associated with the award to be updated.
    :type application_id: int

    :param payload: The data payload for updating the award.
    :type payload: dict

    :param user: The user trying to update the award.
    :type user: models.User

    :return: The updated Application.
    :rtype: models.Application

    :raise HTTPException: Raises an exception with status code 404 and a "Application or award not found"error detail if the application or award does not exist. # noqa

    :raise HTTPException: Raises an exception with status code 403 and a "This application is not ownedby this lender" error detail if the user is not an OCP and does not own the application.# noqa

    :raise HTTPException: Raises an exception if the application status is in the 'OCP_cannot_modify' list (implied by the call to check_application_not_status).
    """  # noqa

    application = (
        models.Application.filter_by(session, "id", application_id)
        .options(defaultload(models.Application.award))
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

    # Update the award, but return the application.
    update_dict = jsonable_encoder(payload, exclude_unset=True)
    application.award.update(session, **update_dict)

    return application


def get_all_active_applications(
    page: int, page_size: int, sort_field: str, sort_order: str, session: Session
) -> serializers.ApplicationListResponse:
    """
    Retrieves all active applications.

    This function queries for all submitted applications,
    The results are sorted according to the provided sort_field and sort_order. Pagination is implemented with the
    page and page_size parameters. The resulting list of applications is wrapped into an ApplicationListResponse.

    :param page: The number of the page to be retrieved. The first page is page 0.
    :type page: int

    :param page_size: The size of the page, i.e., the maximum number of applications to be included in the response.
    :type page_size: int

    :param sort_field: The field by which to sort the applications.
    :type sort_field: str

    :param sort_order: The order in which to sort the applications. Can be either 'asc' or 'desc'.
    :type sort_order: str

    :param session: The database session.
    :type session: Session

    :return: The list of active applications along with pagination information.
    :rtype: serializers.ApplicationListResponse
    """

    sort_direction = desc if sort_order.lower() == "desc" else asc

    applications_query = (
        models.Application.submitted(session)
        .join(models.Award)
        .join(models.Borrower)
        .options(
            joinedload(models.Application.award),
            joinedload(models.Application.borrower),
        )
        .order_by(text(f"{sort_field} {sort_direction.__name__}"))
    )

    total_count = applications_query.count()

    applications = applications_query.offset(page * page_size).limit(page_size).all()

    return serializers.ApplicationListResponse(
        items=applications,
        count=total_count,
        page=page,
        page_size=page_size,
    )


def get_all_fi_applications_emails(session: Session, lender_id, lang: str):
    applications_query = (
        models.Application.submitted_to_lender(session, lender_id)
        .join(models.Borrower)
        .options(
            joinedload(models.Application.borrower),
        )
    )
    applicants_list = []
    for application in applications_query.all():
        applicants_list.append(
            {
                get_translated_string("National Tax ID", lang): application.borrower.legal_identifier,
                get_translated_string("Legal Name", lang): application.borrower.legal_name,
                get_translated_string("Email Address", lang): application.primary_email,
                get_translated_string("Submission Date", lang): application.borrower_submitted_at,
                get_translated_string("Stage", lang): get_translated_string(
                    application.status.name.capitalize(), lang
                ),
            }
        )
    return applicants_list


def get_all_FI_user_applications(
    page: int,
    page_size: int,
    sort_field: str,
    sort_order: str,
    session: Session,
    lender_id,
) -> serializers.ApplicationListResponse:
    """
    Retrieves all applications associated with a specific Financial Institution (FI) user.

    This function queries for all submitted applications,
    and are associated with the provided lender_id. The results are sorted according to the provided sort_field and
    sort_order. Pagination is implemented with the page and page_size parameters. The resulting list of applications
    is wrapped into an ApplicationListResponse.

    :param page: The number of the page to be retrieved. The first page is page 0.
    :type page: int

    :param page_size: The size of the page, i.e., the maximum number of applications to be included in the response.
    :type page_size: int

    :param sort_field: The field by which to sort the applications.
    :type sort_field: str

    :param sort_order: The order in which to sort the applications. Can be either 'asc' or 'desc'.
    :type sort_order: str

    :param session: The database session.
    :type session: Session

    :param lender_id: The ID of the lender (FI user) whose applications are to be retrieved.
    :type lender_id: int

    :return: The list of applications associated with the specified FI user along with pagination information.
    :rtype: serializers.ApplicationListResponse
    """

    sort_direction = desc if sort_order.lower() == "desc" else asc

    applications_query = (
        models.Application.submitted_to_lender(session, lender_id)
        .join(models.Award)
        .join(models.Borrower)
        .options(
            joinedload(models.Application.award),
            joinedload(models.Application.borrower),
        )
        .order_by(text(f"{sort_field} {sort_direction.__name__}"))
    )
    total_count = applications_query.count()

    applications = applications_query.offset(page * page_size).limit(page_size).all()

    return serializers.ApplicationListResponse(
        items=applications,
        count=total_count,
        page=page,
        page_size=page_size,
    )


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
    detail: str = None,
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
        message = "Application status is not {}".format(applicationStatus.name)
        if detail:
            message = detail
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
        )


def check_application_in_status(
    application: models.Application,
    applicationStatus: List[models.ApplicationStatus],
    detail: str = None,
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
        message = "Application status should not be {}".format(application.status.name)
        if detail:
            message = detail
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
        )


def check_application_not_status(
    application: models.Application,
    applicationStatus: List[models.ApplicationStatus],
    detail: str = None,
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
        message = "Application status is {}".format(application.status.name)
        if detail:
            message = detail
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
        )


def update_application_primary_email(application: models.Application, email: str) -> str:
    """
    Updates the primary email of an application.

    This function validates the new email provided. If it's invalid, an HTTP exception is raised.
    If the email is valid, it generates a UUID based on the email and sets it as the application's
    confirmation email token. It then sets the application's pending_email_confirmation attribute
    to True and returns the generated confirmation email token.

    :param application: The application for which the email is to be updated.
    :type application: models.Application

    :param email: The new email.
    :type email: str

    :return: The generated confirmation email token.
    :rtype: str
    """
    if not re.match(valid_email, email):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New email is not valid",
        )
    confirmation_email_token = util.generate_uuid(email)
    application.confirmation_email_token = f"{email}---{confirmation_email_token}"
    application.pending_email_confirmation = True

    return confirmation_email_token


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


def copy_documents(application: models.Application, documents: dict, session: Session):
    """
    Copies provided documents into the database for a given application.

    This function takes in an application and a dictionary of documents, and then copies these documents
    into the database for the provided application. After copying, the new documents are added to the
    application's borrower_documents attribute.

    :param application: The application to copy documents for.
    :type application: models.Application

    :param documents: A dictionary of documents to be copied.
    :type documents: dict

    :param session: The database session to use.
    :type session: Session

    :return: None
    """

    for document in documents:
        data = {
            "application_id": application.id,
            "type": document.type,
            "name": document.name,
            "file": document.file,
            "verified": False,
        }
        new_borrower_document = models.BorrowerDocument.create(session, **data)
        application.borrower_documents.append(new_borrower_document)


def copy_application(application: models.Application, session: Session) -> models.Application:
    """
    Creates a new application that is a copy of the provided one, with some changes.

    This function makes a new application in the database that is a copy of the provided
    application. Some changes are made to the new application's attributes, like a new UUID and
    setting the status to ACCEPTED.

    :param application: The application to copy.
    :type application: models.Application

    :param session: The database session to use.
    :type session: Session

    :raises HTTPException: If there's an error during the copy process.

    :return: The newly created copy of the application.
    :rtype: models.Application
    """

    try:
        data = {
            "award_id": application.award_id,
            "uuid": util.generate_uuid(application.uuid),
            "primary_email": application.primary_email,
            "status": models.ApplicationStatus.ACCEPTED,
            "award_borrower_identifier": application.award_borrower_identifier,
            "borrower_id": application.borrower.id,
            "calculator_data": application.calculator_data,
            "borrower_accepted_at": datetime.now(application.created_at.tzinfo),
        }
        return models.Application.create(session, **data)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"There was a problem copying the application.{e}",
        )


def get_previous_documents(application: models.Application, session: Session):
    """
    Retrieves and copies the borrower documents from the most recent rejected application
    that shares the same award borrower identifier as the given application. The documents
    to be copied are only those whose types are required by the credit product of the
    application.

    This function first queries the database to find the most recent application with the
    provided award borrower identifier that has a status of REJECTED. If there's no such
    application, the function returns. If there is, the function retrieves all the borrower
    documents associated with that application whose types are required by the credit product
    of the given application. The function then copies these documents into the given
    application.

    :param application: The application for which to copy the previous documents.
    :type application: models.Application

    :param session: The database session to use.
    :type session: Session
    """

    document_types = application.credit_product.required_document_types
    document_types_list = [key for key, value in document_types.items() if value]

    lastest_application_id = (
        session.query(models.Application.id)
        .filter(
            models.Application.status == models.ApplicationStatus.REJECTED,
            models.Application.award_borrower_identifier == application.award_borrower_identifier,
        )
        .order_by(models.Application.created_at.desc())
        .first()
    )
    if not lastest_application_id:
        return

    documents = (
        session.query(models.BorrowerDocument)
        .filter(
            models.BorrowerDocument.application_id == lastest_application_id[0],
            models.BorrowerDocument.type.in_(document_types_list),
        )
        .all()
    )

    copy_documents(application, documents, session)


def check_if_application_was_already_copied(application: models.Application, session: Session):
    """
    Checks if a particular application has been already copied.

    This function queries the database to look for an ApplicationAction entry for
    the provided application with the action type set to COPIED_APPLICATION. If
    such an action is found, it raises a HTTPException with a status code of 409
    (CONFLICT) and a detail message indicating that the application has already been copied.

    :param application: The application to check.
    :type application: models.Application

    :param session: The database session to use.
    :type session: Session

    :raises HTTPException: If an ApplicationAction of type COPIED_APPLICATION is found
                        for the given application.
    """

    app_action = (
        session.query(models.ApplicationAction)
        .join(
            models.Application,
            models.Application.id == models.ApplicationAction.application_id,
        )
        .filter(
            models.Application.id == application.id,
            models.ApplicationAction.type == models.ApplicationActionType.COPIED_APPLICATION,
        )
        .options(joinedload(models.ApplicationAction.application))
        .first()
    )

    if app_action:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ERROR_CODES.APPLICATION_ALREADY_COPIED.value,
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
