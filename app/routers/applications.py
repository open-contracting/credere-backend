import io
import logging
import zipfile
from datetime import datetime
from typing import List

import pandas as pd
from botocore.exceptions import ClientError
from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy import and_, text
from sqlalchemy.orm import Session, joinedload

import app.utils.applications as utils
from app import models, parsers, serializers
from app.auth import OCP_only, get_current_user, get_user
from app.aws import CognitoClient, get_cognito_client
from app.db import get_db, transaction_session
from app.i18n import get_translated_string
from app.settings import app_settings
from app.utils import background, tables
from app.utils.statistics import update_statistics
from reportlab_mods import styleSubTitle, styleTitle

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/applications/{id}/reject-application",
    tags=["applications"],
    response_model=models.ApplicationWithRelations,
)
async def reject_application(
    id: int,
    payload: parsers.LenderRejectedApplication,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(get_cognito_client),
    user: models.User = Depends(get_user),
):
    """
    Reject an application:
    Changes the status from "STARTED" to "REJECTED".

    :param id: The ID of the application to reject.
    :type id: int

    :param payload: The rejected application data.
    :type payload: parsers.LenderRejectedApplication

    :param session: The database session.
    :type session: Session

    :param client: The Cognito client.
    :type client: CognitoClient

    :param user: The current user.
    :type user: models.User

    :return: The rejected application with its associated relations.
    :rtype: models.ApplicationWithRelations

    """
    with transaction_session(session):
        application = utils.get_application_by_id(id, session)
        utils.check_FI_user_permission(application, user)
        if application.status not in (
            models.ApplicationStatus.CONTRACT_UPLOADED,
            models.ApplicationStatus.STARTED,
        ):
            message = "Application status is not {} or {}".format(
                models.ApplicationStatus.STARTED.name,
                models.ApplicationStatus.CONTRACT_UPLOADED.name,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=message,
            )
        utils.reject_application(application, payload)
        utils.create_application_action(
            session,
            user.id,
            application.id,
            models.ApplicationActionType.REJECTED_APPLICATION,
            payload,
        )
        options = (
            session.query(models.CreditProduct)
            .join(models.Lender)
            .options(joinedload(models.CreditProduct.lender))
            .filter(
                and_(
                    models.CreditProduct.borrower_size == application.borrower.size,
                    models.CreditProduct.lender_id != application.lender_id,
                    models.CreditProduct.lower_limit <= application.amount_requested,
                    models.CreditProduct.upper_limit >= application.amount_requested,
                )
            )
            .all()
        )
        message_id = client.send_rejected_email_to_sme(application, options)
        utils.create_message(application, models.MessageType.REJECTED_APPLICATION, session, message_id)
        background_tasks.add_task(update_statistics)
        return application


@router.post(
    "/applications/{id}/complete-application",
    tags=["applications"],
    response_model=models.ApplicationWithRelations,
)
async def complete_application(
    id: int,
    payload: parsers.LenderReviewContract,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    user: models.User = Depends(get_user),
    client: CognitoClient = Depends(get_cognito_client),
):
    """
    Complete an application:
    Changes application status from "CONTRACT_UPLOADED" to "COMPLETED".

    :param id: The ID of the application to complete.
    :type id: int

    :param payload: The completed application data.
    :type payload: parsers.LenderReviewContract

    :param session: The database session.
    :type session: Session

    :param user: The current user.
    :type user: models.User

    :param client: The Cognito client.
    :type client: CognitoClient

    :return: The completed application with its associated relations.
    :rtype: models.ApplicationWithRelations

    """
    with transaction_session(session):
        application = utils.get_application_by_id(id, session)
        utils.check_FI_user_permission(application, user)
        utils.check_application_status(application, models.ApplicationStatus.CONTRACT_UPLOADED)
        utils.complete_application(application, payload.disbursed_final_amount)
        application.completed_in_days = background.get_application_days_passed(application, session)
        utils.create_application_action(
            session,
            user.id,
            application.id,
            models.ApplicationActionType.FI_COMPLETE_APPLICATION,
            {
                "disbursed_final_amount": payload.disbursed_final_amount,
            },
        )
        message_id = client.send_application_credit_disbursed(application)
        utils.create_message(
            application,
            models.MessageType.CREDIT_DISBURSED,
            session,
            message_id,
        )
        background_tasks.add_task(update_statistics)
        return application


@router.post(
    "/applications/{id}/approve-application",
    tags=["applications"],
    response_model=models.ApplicationWithRelations,
)
async def approve_application(
    id: int,
    payload: parsers.LenderApprovedData,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(get_cognito_client),
    user: models.User = Depends(get_user),
):
    """
    Approve an application:
    Changes application status from "STARTED" to "APPROVED".

    Sends an email to  SME notifying the current stage of their application.

    :param id: The ID of the application to approve.
    :type id: int

    :param payload: The approved application data.
    :type payload: parsers.LenderApprovedData

    :param session: The database session.
    :type session: Session

    :param client: The Cognito client.
    :type client: CognitoClient

    :param user: The current user.
    :type user: models.User

    :return: The approved application with its associated relations.
    :rtype: models.ApplicationWithRelations

    """
    with transaction_session(session):
        application = utils.get_application_by_id(id, session)
        utils.check_FI_user_permission(application, user)
        utils.check_application_status(application, models.ApplicationStatus.STARTED)
        utils.approve_application(application, payload)
        utils.create_application_action(
            session,
            user.id,
            application.id,
            models.ApplicationActionType.APPROVED_APPLICATION,
            payload,
        )

        message_id = client.send_application_approved_to_sme(application)
        utils.create_message(
            application,
            models.MessageType.APPROVED_APPLICATION,
            session,
            message_id,
        )
        background_tasks.add_task(update_statistics)
        return application


@router.post(
    "/applications/change-email",
    tags=["applications"],
    response_model=parsers.ChangeEmail,
)
async def change_email(
    payload: parsers.ChangeEmail,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(get_cognito_client),
):
    """
    Change the email address for an application.

    :param payload: The data for changing the email address.
    :type payload: parsers.ChangeEmail

    :param session: The database session.
    :type session: Session

    :param client: The Cognito client.
    :type client: CognitoClient

    :return: The data for changing the email address.
    :rtype: parsers.ChangeEmail

    """
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)
        old_email = application.primary_email
        confirmation_email_token = utils.update_application_primary_email(application, payload.new_email)
        utils.create_application_action(
            session,
            None,
            application.id,
            models.ApplicationActionType.MSME_CHANGE_EMAIL,
            payload,
        )

        external_message_id = client.send_new_email_confirmation_to_sme(
            application.borrower.legal_name,
            payload.new_email,
            old_email,
            confirmation_email_token,
            application.uuid,
        )

        utils.create_message(
            application,
            models.MessageType.EMAIL_CHANGE_CONFIRMATION,
            session,
            external_message_id,
        )

        return payload


@router.post(
    "/applications/confirm-change-email",
    tags=["applications"],
    response_model=parsers.ChangeEmail,
)
async def confirm_email(
    payload: parsers.ConfirmNewEmail,
    session: Session = Depends(get_db),
):
    """
    Confirm the email address change for an application.

    :param payload: The data for confirming the email address change.
    :type payload: parsers.ConfirmNewEmail

    :param session: The database session.
    :type session: Session

    :return: The data for confirming the email address change.
    :rtype: parsers.ChangeEmail

    """
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)

        utils.check_pending_email_confirmation(application, payload.confirmation_email_token)

        utils.create_application_action(
            session,
            None,
            application.id,
            models.ApplicationActionType.MSME_CONFIRM_EMAIL,
            payload,
        )

        return parsers.ChangeEmail(new_email=application.primary_email, uuid=application.uuid)


@router.get(
    "/applications/documents/id/{id}",
    tags=["applications"],
)
async def get_borrower_document(
    id: int,
    session: Session = Depends(get_db),
    user: models.User = Depends(get_user),
):
    """
    Retrieve a borrower document by its ID and stream the file content as a response.

    :param id: The ID of the borrower document to retrieve.
    :type id: int

    :param session: The database session.
    :type session: Session

    :param user: The current user.
    :type user: models.User

    :return: A streaming response with the borrower document file content.
    :rtype: StreamingResponse

    """
    with transaction_session(session):
        document = models.BorrowerDocument.first_by(session, "id", id)
        utils.get_file(document, user, session)

        def file_generator():
            yield document.file

        headers = {
            "Content-Disposition": f'attachment; filename="{document.name}"',
            "Content-Type": "application/octet-stream",
        }
        return StreamingResponse(file_generator(), headers=headers)


@router.get(
    "/applications/{application_id}/download-application/{lang}",
    tags=["applications"],
)
async def download_application(
    application_id: int,
    lang: str,
    session: Session = Depends(get_db),
    user: models.User = Depends(get_user),
):
    """
    Retrieve all documents related to an application and stream them as a zip file.

    :param application_id: The ID of the application to retrieve documents for.
    :type application_id: int

    :param session: The database session.
    :type session: Session

    :param user: The current user.
    :type user: models.User

    :return: A streaming response with a zip file containing the documents.
    :rtype: StreamingResponse
    """
    with transaction_session(session):
        application = utils.get_application_by_id(application_id, session)

        borrower = application.borrower
        award = application.award

        documents = (
            session.query(models.BorrowerDocument)
            .filter(models.BorrowerDocument.application_id == application_id)
            .all()
        )

        previous_awards = utils.get_previous_awards(application, session)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)

        elements = []

        elements.append(Paragraph(get_translated_string("Application Details", lang), styleTitle))

        elements.append(tables.create_application_table(application, lang))
        elements.append(Spacer(1, 20))
        elements.append(tables.create_borrower_table(borrower, application, lang))
        elements.append(Spacer(1, 20))
        elements.append(tables.create_documents_table(documents, lang))
        elements.append(Spacer(1, 20))
        elements.append(tables.create_award_table(award, lang))

        if previous_awards and len(previous_awards) > 0:
            elements.append(Spacer(1, 20))
            elements.append(Paragraph(get_translated_string("Previous Public Sector Contracts", lang), styleSubTitle))
            for award in previous_awards:
                elements.append(tables.create_award_table(award, lang))
                elements.append(Spacer(1, 20))

        doc.build(elements)

        name = get_translated_string("Application Details", lang).replace(" ", "_")
        filename = f"{name}-{application.borrower.legal_identifier}" + f"-{application.award.source_contract_id}.pdf"

        in_memory_zip = io.BytesIO()
        with zipfile.ZipFile(in_memory_zip, "w") as zip_file:
            zip_file.writestr(filename, buffer.getvalue())
            for document in documents:
                zip_file.writestr(document.name, document.file)

        application_action_type = (
            models.ApplicationActionType.OCP_DOWNLOAD_APPLICATION
            if user.is_OCP()
            else models.ApplicationActionType.FI_DOWNLOAD_APPLICATION
        )
        utils.create_application_action(session, user.id, application.id, application_action_type, {})

        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/zip",
        }

        return StreamingResponse(io.BytesIO(in_memory_zip.getvalue()), headers=headers)


@router.post(
    "/applications/upload-document",
    tags=["applications"],
    response_model=models.BorrowerDocumentBase,
)
async def upload_document(
    file: UploadFile,
    uuid: str = Form(...),
    type: str = Form(...),
    session: Session = Depends(get_db),
):
    """
    Upload a document for an application.

    :param file: The uploaded file.
    :type file: UploadFile

    :param uuid: The UUID of the application.
    :type uuid: str

    :param type: The type of the document.
    :type type: str

    :param session: The database session.
    :type session: Session

    :return: The created or updated borrower document.
    :rtype: models.BorrowerDocumentBase

    """
    with transaction_session(session):
        new_file, filename = utils.validate_file(file)
        application = utils.get_application_by_uuid(uuid, session)
        if not application.pending_documents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot upload document at this stage",
            )

        document = utils.create_or_update_borrower_document(filename, application, type, session, new_file)

        utils.create_application_action(
            session,
            None,
            application.id,
            models.ApplicationActionType.MSME_UPLOAD_DOCUMENT,
            {"file_name": filename},
        )

        return document


@router.post(
    "/applications/upload-contract",
    tags=["applications"],
    response_model=models.BorrowerDocumentBase,
)
async def upload_contract(
    file: UploadFile,
    uuid: str = Form(...),
    session: Session = Depends(get_db),
):
    """
    Upload a contract document for an application.

    :param file: The uploaded file.
    :type file: UploadFile

    :param uuid: The UUID of the application.
    :type uuid: str

    :param session: The database session.
    :type session: Session

    :return: The created or updated borrower document representing the contract.
    :rtype: models.BorrowerDocumentBase

    """
    with transaction_session(session):
        new_file, filename = utils.validate_file(file)
        application = utils.get_application_by_uuid(uuid, session)

        utils.check_application_status(application, models.ApplicationStatus.APPROVED)

        document = utils.create_or_update_borrower_document(
            filename,
            application,
            models.BorrowerDocumentType.SIGNED_CONTRACT,
            session,
            new_file,
        )

        return document


@router.post(
    "/applications/confirm-upload-contract",
    tags=["applications"],
    response_model=serializers.ApplicationResponse,
)
async def confirm_upload_contract(
    payload: parsers.UploadContractConfirmation,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(get_cognito_client),
):
    """
    Confirm the upload of a contract document for an application.

    Changes application status from "CONTRACT_UPLOADED" to "CONTRACT_ACCEPTED".

    Sends an email to SME notifying the current stage of their application.

    :param payload: The confirmation data for the uploaded contract.
    :type payload: parsers.UploadContractConfirmation

    :param session: The database session.
    :type session: Session

    :param client: The Cognito client.
    :type client: CognitoClient

    :return: The application response containing the updated application and related entities.
    :rtype: serializers.ApplicationResponse

    """
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)
        utils.check_application_status(application, models.ApplicationStatus.APPROVED)

        FI_message_id, SME_message_id = client.send_upload_contract_notifications(application)

        application.contract_amount_submitted = payload.contract_amount_submitted
        application.status = models.ApplicationStatus.CONTRACT_UPLOADED
        application.borrower_uploaded_contract_at = datetime.now(application.created_at.tzinfo)

        utils.create_message(
            application,
            models.MessageType.CONTRACT_UPLOAD_CONFIRMATION_TO_FI,
            session,
            FI_message_id,
        )

        utils.create_message(
            application,
            models.MessageType.CONTRACT_UPLOAD_CONFIRMATION,
            session,
            SME_message_id,
        )

        utils.create_application_action(
            session,
            None,
            application.id,
            models.ApplicationActionType.MSME_UPLOAD_CONTRACT,
            {
                "contract_amount_submitted": payload.contract_amount_submitted,
            },
        )

        return serializers.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
            lender=application.lender,
            documents=application.borrower_documents,
            creditProduct=application.credit_product,
        )


@router.post(
    "/applications/{id}/upload-compliance",
    tags=["applications"],
    response_model=models.BorrowerDocumentBase,
)
async def upload_compliance(
    id: int,
    file: UploadFile,
    session: Session = Depends(get_db),
    user: models.User = Depends(get_user),
):
    """
    Upload a compliance document for an application.

    :param id: The ID of the application.
    :type id: int

    :param file: The uploaded file.
    :type file: UploadFile

    :param session: The database session.
    :type session: Session

    :param user: The current user.
    :type user: models.User

    :return: The created or updated borrower document representing the compliance report.
    :rtype: models.BorrowerDocumentBase

    """
    with transaction_session(session):
        new_file, filename = utils.validate_file(file)
        application = utils.get_application_by_id(id, session)

        utils.check_FI_user_permission(application, user)

        document = utils.create_or_update_borrower_document(
            filename,
            application,
            models.BorrowerDocumentType.COMPLIANCE_REPORT,
            session,
            new_file,
            True,
        )

        utils.create_application_action(
            session,
            None,
            application.id,
            models.ApplicationActionType.FI_UPLOAD_COMPLIANCE,
            {"file_name": filename},
        )

        return document


@router.put(
    "/applications/{id}/verify-data-field",
    tags=["applications"],
    response_model=models.ApplicationWithRelations,
)
async def verify_data_field(
    id: int,
    payload: parsers.UpdateDataField,
    session: Session = Depends(get_db),
    user: models.User = Depends(get_user),
):
    """
    Verify and update a data field in an application.

    :param id: The ID of the application.
    :type id: int

    :param payload: The data field update payload.
    :type payload: parsers.UpdateDataField

    :param session: The database session.
    :type session: Session

    :param user: The current user.
    :type user: models.User

    :return: The updated application with its associated relations.
    :rtype: models.ApplicationWithRelations

    """
    with transaction_session(session):
        application = utils.get_application_by_id(id, session)
        utils.check_application_in_status(
            application,
            [
                models.ApplicationStatus.STARTED,
                models.ApplicationStatus.INFORMATION_REQUESTED,
            ],
        )

        utils.check_FI_user_permission(application, user)
        utils.update_data_field(application, payload)

        utils.create_application_action(
            session,
            user.id,
            application.id,
            models.ApplicationActionType.DATA_VALIDATION_UPDATE,
            payload,
        )

        return application


@router.put(
    "/applications/documents/{document_id}/verify-document",
    tags=["applications"],
    response_model=models.ApplicationWithRelations,
)
async def verify_document(
    document_id: int,
    payload: parsers.VerifyBorrowerDocument,
    session: Session = Depends(get_db),
    user: models.User = Depends(get_user),
):
    """
    Verify a borrower document in an application.

    :param document_id: The ID of the borrower document.
    :type document_id: int

    :param payload: The document verification payload.
    :type payload: parsers.VerifyBorrowerDocument

    :param session: The database session.
    :type session: Session

    :param user: The current user.
    :type user: models.User

    :return: The updated application with its associated relations.
    :rtype: models.ApplicationWithRelations

    """
    with transaction_session(session):
        document = utils.get_document_by_id(document_id, session)
        utils.check_FI_user_permission(document.application, user)
        utils.check_application_in_status(
            document.application,
            [
                models.ApplicationStatus.STARTED,
                models.ApplicationStatus.INFORMATION_REQUESTED,
            ],
        )

        document.verified = payload.verified

        utils.create_application_action(
            session,
            user.id,
            document.application.id,
            models.ApplicationActionType.BORROWER_DOCUMENT_UPDATE,
            payload,
        )

        return document.application


@router.put(
    "/applications/{application_id}/award",
    tags=["applications"],
    response_model=models.ApplicationWithRelations,
)
async def update_application_award(
    application_id: int,
    payload: parsers.AwardUpdate,
    user: models.User = Depends(get_user),
    session: Session = Depends(get_db),
):
    """
    Update the award details of an application.

    :param application_id: The ID of the application.
    :type application_id: int

    :param payload: The award update payload.
    :type payload: parsers.AwardUpdate

    :param user: The current user.
    :type user: models.User

    :param session: The database session.
    :type session: Session

    :return: The updated application with its associated relations.
    :rtype: models.ApplicationWithRelations

    """
    with transaction_session(session):
        application = utils.update_application_award(session, application_id, payload, user)
        utils.create_application_action(
            session,
            user.id,
            application_id,
            models.ApplicationActionType.AWARD_UPDATE,
            payload,
        )

        application = utils.get_modified_data_fields(application, session)
        return application


@router.put(
    "/applications/{application_id}/borrower",
    tags=["applications"],
    response_model=models.ApplicationWithRelations,
)
async def update_application_borrower(
    application_id: int,
    payload: parsers.BorrowerUpdate,
    user: models.User = Depends(get_user),
    session: Session = Depends(get_db),
):
    """
    Update the borrower details of an application.

    :param application_id: The ID of the application.
    :type application_id: int

    :param payload: The borrower update payload.
    :type payload: parsers.BorrowerUpdate

    :param user: The current user.
    :type user: models.User

    :param session: The database session.
    :type session: Session

    :return: The updated application with its associated relations.
    :rtype: models.ApplicationWithRelations

    """
    with transaction_session(session):
        application = utils.update_application_borrower(session, application_id, payload, user)

        utils.create_application_action(
            session,
            user.id,
            application_id,
            models.ApplicationActionType.BORROWER_UPDATE,
            payload,
        )

        application = utils.get_modified_data_fields(application, session)
        return application


@router.get(
    "/applications/admin-list",
    tags=["applications"],
    response_model=serializers.ApplicationListResponse,
)
@OCP_only()
async def get_applications_list(
    page: int = Query(0, ge=0),
    page_size: int = Query(10, gt=0),
    sort_field: str = Query("application.created_at"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: models.User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """
    Get a paginated list of applications for administrative purposes.

    :param page: The page number of the application list (default: 0).
    :type page: int

    :param page_size: The number of applications per page (default: 10).
    :type page_size: int

    :param sort_field: The field to sort the applications by (default: "application.created_at").
    :type sort_field: str

    :param sort_order: The sort order of the applications ("asc" or "desc", default: "asc").
    :type sort_order: str

    :param current_user: The current user authenticated.
    :type current_user: models.User

    :param session: The database session.
    :type session: Session

    :return: The paginated list of applications.
    :rtype: serializers.ApplicationListResponse

    :raise: lumache.OCPOnlyError if the current user is not authorized.

    """
    return utils.get_all_active_applications(page, page_size, sort_field, sort_order, session)


@router.get(
    "/applications/id/{id}",
    tags=["applications"],
    response_model=models.ApplicationWithRelations,
)
async def get_application(
    id: int,
    user: models.User = Depends(get_user),
    session: Session = Depends(get_db),
):
    """
    Retrieve an application by its ID.

    :param id: The ID of the application to retrieve.
    :type id: int

    :param user: The current user.
    :type user: models.User

    :param session: The database session.
    :type session: Session

    :return: The application with the specified ID and its associated relations.
    :rtype: models.ApplicationWithRelations

    :raise: HTTPException with status code 401 if the user is not authorized to view the application.

    """
    application = utils.get_application_by_id(id, session)
    application = utils.get_modified_data_fields(application, session)

    if user.is_OCP():
        return application

    if user.lender_id != application.lender_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized to view this application",
        )

    return application


@router.post(
    "/applications/{id}/start",
    tags=["applications"],
    response_model=models.ApplicationWithRelations,
)
async def start_application(
    id: int,
    background_tasks: BackgroundTasks,
    user: models.User = Depends(get_user),
    session: Session = Depends(get_db),
):
    """
    Start an application:
    Changes application status from "SUBMITTED" to "STARTED".

    :param id: The ID of the application to start.
    :type id: int

    :param user: The current user.
    :type user: models.User

    :param session: The database session.
    :type session: Session

    :return: The started application with its associated relations.
    :rtype: models.ApplicationWithRelations

    :raise: HTTPException with status code 401 if the user is not authorized to start the application.

    """
    with transaction_session(session):
        application = models.Application.first_by(session, "id", id)
        utils.check_application_status(application, models.ApplicationStatus.SUBMITTED)

        if user.lender_id != application.lender_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized to start this application",
            )

        application.status = models.ApplicationStatus.STARTED
        application.lender_started_at = datetime.now(application.created_at.tzinfo)
        background_tasks.add_task(update_statistics)
        return application


@router.get(
    "/applications/export/{lang}",
    tags=["applications"],
    response_class=StreamingResponse,
)
async def export_applications(
    lang: str,
    user: models.User = Depends(get_user),
    session: Session = Depends(get_db),
):
    df = pd.DataFrame(utils.get_all_fi_applications_emails(session, user.lender_id, lang))
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=export.csv"
    return response


@router.get(
    "/applications",
    tags=["applications"],
    response_model=serializers.ApplicationListResponse,
)
async def get_applications(
    page: int = Query(0, ge=0),
    page_size: int = Query(10, gt=0),
    sort_field: str = Query("application.created_at"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    user: models.User = Depends(get_user),
    session: Session = Depends(get_db),
):
    """
    Get a paginated list of applications for a specific user.

    :param page: The page number of the application list (default: 0).
    :type page: int

    :param page_size: The number of applications per page (default: 10).
    :type page_size: int

    :param sort_field: The field to sort the applications by (default: "application.created_at").
    :type sort_field: str

    :param sort_order: The sort order of the applications ("asc" or "desc", default: "asc").
    :type sort_order: str

    :param user: The current user.
    :type user: models.User

    :param session: The database session.
    :type session: Session

    :return: The paginated list of applications for the specific user.
    :rtype: serializers.ApplicationListResponse

    """
    return utils.get_all_FI_user_applications(page, page_size, sort_field, sort_order, session, user.lender_id)


@router.get(
    "/applications/uuid/{uuid}",
    tags=["applications"],
    response_model=serializers.ApplicationResponse,
)
async def application_by_uuid(uuid: str, session: Session = Depends(get_db)):
    """
    Retrieve an application by its UUID.

    :param uuid: The UUID of the application to retrieve.
    :type uuid: str

    :param session: The database session.
    :type session: Session

    :return: The application with the specified UUID and its associated entities.
    :rtype: serializers.ApplicationResponse

    :raise: HTTPException with status code 404 if the application is expired.

    """
    application = utils.get_application_by_uuid(uuid, session)
    utils.check_is_application_expired(application)

    return serializers.ApplicationResponse(
        application=application,
        borrower=application.borrower,
        award=application.award,
        lender=application.lender,
        documents=application.borrower_documents,
        creditProduct=application.credit_product,
    )


@router.post(
    "/applications/access-scheme",
    tags=["applications"],
    response_model=serializers.ApplicationResponse,
)
async def access_scheme(
    payload: parsers.ApplicationBase,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
):
    """
    Access the scheme for an application.

    Changes the status from PENDING to ACCEPTED.

    Search for previous awards for the borrower and add them to the application.


    :param payload: The application data.
    :type payload: parsers.ApplicationBase

    :param background_tasks: The background tasks to be executed.
    :type background_tasks: BackgroundTasks

    :param session: The database session.
    :type session: Session

    :return: The application response containing the updated application, borrower, and award.
    :rtype: serializers.ApplicationResponse

    :raise: HTTPException with status code 404 if the application is expired or not in the PENDING status.

    """
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)
        utils.check_is_application_expired(application)
        utils.check_application_status(application, models.ApplicationStatus.PENDING)

        current_time = datetime.now(application.created_at.tzinfo)
        application.borrower_accepted_at = current_time
        application.status = models.ApplicationStatus.ACCEPTED
        application.expired_at = None

        background_tasks.add_task(background.fetch_previous_awards, application.borrower)
        background_tasks.add_task(update_statistics)

        return serializers.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
        )


@router.post(
    "/applications/credit-product-options",
    tags=["applications"],
    response_model=serializers.CreditProductListResponse,
)
async def credit_product_options(
    payload: parsers.ApplicationCreditOptions,
    session: Session = Depends(get_db),
):
    """
    Get the available credit product options for an application.

    :param payload: The application credit options.
    :type payload: parsers.ApplicationCreditOptions

    :param session: The database session.
    :type session: Session

    :return: The credit product list response containing the available loans and credit lines.
    :rtype: serializers.CreditProductListResponse

    :raise: HTTPException with status code 404 if the application is expired, not in the ACCEPTED status, or if the previous lenders are not found. # noqa

    """
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)

        previous_lenders = utils.get_previous_lenders(application.award_borrower_identifier, session)
        utils.check_is_application_expired(application)
        utils.check_application_status(application, models.ApplicationStatus.ACCEPTED)

        filter = None
        if application.borrower.type.lower() == "persona natural colombiana":
            filter = text(f"(borrower_types->>'{models.BorrowerType.NATURAL_PERSON.value}')::boolean is True")
        else:
            filter = text(f"(borrower_types->>'{models.BorrowerType.LEGAL_PERSON.value}')::boolean is True")

        loans_query = (
            session.query(models.CreditProduct)
            .join(models.Lender)
            .options(joinedload(models.CreditProduct.lender))
            .filter(
                and_(
                    models.CreditProduct.type == models.CreditType.LOAN,
                    models.CreditProduct.borrower_size == payload.borrower_size,
                    models.CreditProduct.lower_limit <= payload.amount_requested,
                    models.CreditProduct.upper_limit >= payload.amount_requested,
                    ~models.Lender.id.in_(previous_lenders),
                    filter,
                )
            )
        )

        credit_lines_query = (
            session.query(models.CreditProduct)
            .join(models.Lender)
            .options(joinedload(models.CreditProduct.lender))
            .filter(
                and_(
                    models.CreditProduct.type == models.CreditType.CREDIT_LINE,
                    models.CreditProduct.borrower_size == payload.borrower_size,
                    models.CreditProduct.lower_limit <= payload.amount_requested,
                    models.CreditProduct.upper_limit >= payload.amount_requested,
                    ~models.Lender.id.in_(previous_lenders),
                    filter,
                )
            )
        )

        loans = loans_query.all()
        credit_lines = credit_lines_query.all()

        return serializers.CreditProductListResponse(loans=loans, credit_lines=credit_lines)


@router.post(
    "/applications/select-credit-product",
    tags=["applications"],
    response_model=serializers.ApplicationResponse,
)
async def select_credit_product(
    payload: parsers.ApplicationSelectCreditProduct,
    session: Session = Depends(get_db),
):
    """
    Select a credit product for an application.

    :param payload: The application credit product selection payload.
    :type payload: parsers.ApplicationSelectCreditProduct

    :param session: The database session.
    :type session: Session

    :return: The application response containing the updated application, borrower, award, lender, documents, and credit product. # noqa: E501
    :rtype: serializers.ApplicationResponse

    :raise: HTTPException with status code 404 if the application is expired, not in the ACCEPTED status, or if the calculator data is invalid. # noqa: E501

    """
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)
        utils.check_is_application_expired(application)
        utils.check_application_status(application, models.ApplicationStatus.ACCEPTED)

        calculator_data = utils.get_calculator_data(payload)

        application.calculator_data = calculator_data
        application.credit_product_id = payload.credit_product_id
        current_time = datetime.now(application.created_at.tzinfo)
        application.borrower_credit_product_selected_at = current_time

        application.borrower.size = payload.borrower_size
        application.borrower.sector = payload.sector

        utils.create_application_action(
            session,
            None,
            application.id,
            models.ApplicationActionType.APPLICATION_CALCULATOR_DATA_UPDATE,
            payload,
        )
        return serializers.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
            lender=application.lender,
            documents=application.borrower_documents,
            creditProduct=application.credit_product,
        )


@router.post(
    "/applications/rollback-select-credit-product",
    tags=["applications"],
    response_model=serializers.ApplicationResponse,
)
async def rollback_select_credit_product(
    payload: parsers.ApplicationBase,
    session: Session = Depends(get_db),
):
    """
    Rollback the selection of a credit product for an application.

    :param payload: The application data.
    :type payload: parsers.ApplicationBase

    :param session: The database session.
    :type session: Session

    :return: The application response containing the updated application, borrower, and award.
    :rtype: serializers.ApplicationResponse

    :raise: HTTPException with status code 400 if the credit product is not selected or if the lender is already assigned. # noqa: E501

    """
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)
        utils.check_is_application_expired(application)
        utils.check_application_status(application, models.ApplicationStatus.ACCEPTED)

        if not application.credit_product_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credit product not selected",
            )

        if application.lender_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot rollback at this stage",
            )

        application.credit_product_id = None
        application.borrower_credit_product_selected_at = None
        return serializers.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
        )


@router.post(
    "/applications/confirm-credit-product",
    tags=["applications"],
    response_model=serializers.ApplicationResponse,
)
async def confirm_credit_product(
    payload: parsers.ApplicationBase,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
):
    """
    Confirm the selected credit product for an application.

    :param payload: The application data.
    :type payload: parsers.ApplicationBase

    :param session: The database session.
    :type session: Session

    :return: The application response containing the updated application, borrower, award, lender, documents, and credit product. # noqa: E501

    :rtype: serializers.ApplicationResponse

    :raise: HTTPException with status code 400 if the credit product is not selected or not found.

    """
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)
        utils.check_is_application_expired(application)
        utils.check_application_status(application, models.ApplicationStatus.ACCEPTED)

        if not application.credit_product_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credit product not selected",
            )

        creditProduct = models.CreditProduct.first_by(session, "id", application.credit_product_id)
        if not creditProduct:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credit product not found",
            )

        application.lender_id = creditProduct.lender_id
        application.amount_requested = application.calculator_data.get("amount_requested", None)
        application.repayment_years = application.calculator_data.get("repayment_years", None)
        application.repayment_months = application.calculator_data.get("repayment_months", None)
        application.payment_start_date = application.calculator_data.get("payment_start_date", None)

        application.pending_documents = True
        utils.get_previous_documents(application, session)
        utils.create_application_action(
            session,
            None,
            application.id,
            models.ApplicationActionType.APPLICATION_CONFIRM_CREDIT_PRODUCT,
            {},
        )
        background_tasks.add_task(update_statistics)
        return serializers.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
            lender=application.lender,
            documents=application.borrower_documents,
            creditProduct=application.credit_product,
        )


@router.post(
    "/applications/submit",
    tags=["applications"],
    response_model=serializers.ApplicationResponse,
)
async def update_apps_send_notifications(
    payload: parsers.ApplicationBase,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(get_cognito_client),
):
    """
    Changes application status from "'ACCEPTED" to "SUBMITTED".
    Sends a notification to OCP and FI user.

    This operation also ensures that the credit product and lender are selected before updating the status.

    :param payload: The application data to update.
    :type payload: parsers.ApplicationBase

    :param session: The database session.
    :type session: Session

    :param client: The Cognito client.
    :type client: CognitoClient

    :return: The updated application with borrower, award and lender details.
    :rtype: serializers.ApplicationResponse

    :raises HTTPException: If credit product or lender is not selected, or if there's an error in submitting the application. # noqa: E501
    """
    with transaction_session(session):
        try:
            application = utils.get_application_by_uuid(payload.uuid, session)
            utils.check_application_status(application, models.ApplicationStatus.ACCEPTED)

            if not application.credit_product_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Credit product not selected",
                )

            if not application.lender:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Lender not selected",
                )

            application.status = models.ApplicationStatus.SUBMITTED
            current_time = datetime.now(application.created_at.tzinfo)
            application.borrower_submitted_at = current_time
            application.pending_documents = False

            client.send_notifications_of_new_applications(
                ocp_email_group=app_settings.ocp_email_group,
                lender_name=application.lender.name,
                lender_email_group=application.lender.email_group,
            )
            message_id = client.send_application_submission_completed(application)
            utils.create_message(
                application,
                models.MessageType.SUBMITION_COMPLETE,
                session,
                message_id,
            )
            background_tasks.add_task(update_statistics)
            return serializers.ApplicationResponse(
                application=application,
                borrower=application.borrower,
                award=application.award,
                lender=application.lender,
            )
        except ClientError as e:
            logger.exception(e)
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="There was an error submiting the application",
            )


@router.post(
    "/applications/email-sme/{id}",
    tags=["applications"],
    response_model=models.ApplicationWithRelations,
)
async def email_sme(
    id: int,
    payload: parsers.ApplicationEmailSme,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(get_cognito_client),
    user: models.User = Depends(get_user),
):
    """
    Send an email to SME and update the application status:
    Changes the application status from "STARTED" to "INFORMATION_REQUESTED".
    sends an email to SME notifying the request.

    :param id: The ID of the application.
    :type id: int

    :param payload: The payload containing the message to send to SME.
    :type payload: parsers.ApplicationEmailSme

    :param session: The database session.
    :type session: Session

    :param client: The Cognito client.
    :type client: CognitoClient

    :param user: The current user.
    :type user: models.User

    :return: The updated application with its associated relations.
    :rtype: models.ApplicationWithRelations

    :raises HTTPException: If there's an error in sending the email to SME.
    """

    with transaction_session(session):
        try:
            application = utils.get_application_by_id(id, session)
            utils.check_FI_user_permission(application, user)
            utils.check_application_status(application, models.ApplicationStatus.STARTED)
            application.status = models.ApplicationStatus.INFORMATION_REQUESTED
            current_time = datetime.now(application.created_at.tzinfo)
            application.information_requested_at = current_time
            application.pending_documents = True

            message_id = client.send_request_to_sme(
                application.uuid,
                application.lender.name,
                payload.message,
                application.primary_email,
            )

            utils.create_application_action(
                session,
                user.id,
                application.id,
                models.ApplicationActionType.FI_REQUEST_INFORMATION,
                payload,
            )

            new_message = models.Message(
                application_id=application.id,
                body=payload.message,
                lender_id=application.lender.id,
                type=models.MessageType.FI_MESSAGE,
                external_message_id=message_id,
            )
            session.add(new_message)
            session.commit()
            background_tasks.add_task(update_statistics)
            return application
        except ClientError as e:
            logger.exception(e)
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="There was an error",
            )


@router.post(
    "/applications/complete-information-request",
    tags=["applications"],
    response_model=serializers.ApplicationResponse,
)
async def complete_information_request(
    payload: parsers.ApplicationBase,
    background_tasks: BackgroundTasks,
    client: CognitoClient = Depends(get_cognito_client),
    session: Session = Depends(get_db),
):
    """
    Complete the information request for an application:
    Changes the application from "INFORMATION REQUESTED" status back to "STARTED" and updates the pending documents status. # noqa: E501

    This operation also sends a notification about the uploaded documents to the FI.

    :param payload: The application data to update.
    :type payload: parsers.ApplicationBase

    :param client: The Cognito client.
    :type client: CognitoClient

    :param session: The database session.
    :type session: Session

    :return: The updated application with borrower, award, lender, and documents details.
    :rtype: serializers.ApplicationResponse

    """

    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)
        utils.check_application_status(application, models.ApplicationStatus.INFORMATION_REQUESTED)

        application.status = models.ApplicationStatus.STARTED
        application.pending_documents = False

        utils.create_application_action(
            session,
            None,
            application.id,
            models.ApplicationActionType.MSME_UPLOAD_ADDITIONAL_DOCUMENT_COMPLETED,
            payload,
        )

        message_id = client.send_upload_documents_notifications(application.lender.email_group)

        utils.create_message(
            application,
            models.ApplicationActionType.BORROWER_DOCUMENT_UPDATE,
            session,
            message_id,
        )
        background_tasks.add_task(update_statistics)
        return serializers.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
            lender=application.lender,
            documents=application.borrower_documents,
        )


@router.post(
    "/applications/decline",
    tags=["applications"],
    response_model=serializers.ApplicationResponse,
)
async def decline(
    payload: parsers.ApplicationDeclinePayload,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
):
    """
    Decline an application.
    Changes application status from "PENDING" to "DECLINED".

    :param payload: The application decline payload.
    :type payload: parsers.ApplicationDeclinePayload

    :param session: The database session.
    :type session: Session

    :return: The application response containing the updated application, borrower, and award.
    :rtype: serializers.ApplicationResponse

    :raise: HTTPException with status code 400 if the application is not in the PENDING status.

    """
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)
        utils.check_is_application_expired(application)
        utils.check_application_status(application, models.ApplicationStatus.PENDING)

        borrower_declined_data = vars(payload)
        borrower_declined_data.pop("uuid")

        application.borrower_declined_data = borrower_declined_data
        application.status = models.ApplicationStatus.DECLINED
        current_time = datetime.now(application.created_at.tzinfo)
        application.borrower_declined_at = current_time

        if payload.decline_all:
            application.borrower.status = models.BorrowerStatus.DECLINE_OPPORTUNITIES
            application.borrower.declined_at = current_time
        background_tasks.add_task(update_statistics)
        return serializers.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
        )


@router.post(
    "/applications/rollback-decline",
    tags=["applications"],
    response_model=serializers.ApplicationResponse,
)
async def rollback_decline(
    payload: parsers.ApplicationBase,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
):
    """
    Rollback the decline of an application.

    :param payload: The application base payload.
    :type payload: parsers.ApplicationBase

    :param session: The database session.
    :type session: Session

    :return: The application response containing the updated application, borrower, and award.
    :rtype: serializers.ApplicationResponse

    :raise: HTTPException with status code 400 if the application is not in the DECLINED status.

    """
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)
        utils.check_is_application_expired(application)
        utils.check_application_status(application, models.ApplicationStatus.DECLINED)

        application.borrower_declined_data = {}
        application.status = models.ApplicationStatus.PENDING
        application.borrower_declined_at = None

        if application.borrower.status == models.BorrowerStatus.DECLINE_OPPORTUNITIES:
            application.borrower.status = models.BorrowerStatus.ACTIVE
            application.borrower.declined_at = None
        background_tasks.add_task(update_statistics)
        return serializers.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
        )


@router.post(
    "/applications/decline-feedback",
    tags=["applications"],
    response_model=serializers.ApplicationResponse,
)
async def decline_feedback(
    payload: parsers.ApplicationDeclineFeedbackPayload,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
):
    """
    Provide feedback for a declined application.

    :param payload: The application decline feedback payload.
    :type payload: parsers.ApplicationDeclineFeedbackPayload

    :param session: The database session.
    :type session: Session

    :return: The application response containing the updated application, borrower, and award.
    :rtype: serializers.ApplicationResponse

    :raise: HTTPException with status code 400 if the application is not in the DECLINED status.

    """
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)
        utils.check_is_application_expired(application)
        utils.check_application_status(application, models.ApplicationStatus.DECLINED)

        borrower_declined_preferences_data = vars(payload)
        borrower_declined_preferences_data.pop("uuid")

        application.borrower_declined_preferences_data = borrower_declined_preferences_data
        background_tasks.add_task(update_statistics)
        return serializers.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
        )


@router.get(
    "/applications/{id}/previous-awards",
    tags=["applications"],
    response_model=List[models.Award],
)
async def previous_contracts(
    id: int,
    user: models.User = Depends(get_user),
    session: Session = Depends(get_db),
):
    """
    Get the previous awards associated with an application.

    :param id: The ID of the application.
    :type id: int

    :param user: The current user authenticated.
    :type user: models.User

    :param session: The database session.
    :type session: Session

    :return: A list of previous awards associated with the application.
    :rtype: List[models.Award]

    :raise: HTTPException with status code 401 if the user is not authorized to access the application.

    """
    with transaction_session(session):
        application = utils.get_application_by_id(id, session)
        utils.check_FI_user_permission_or_OCP(application, user)

        return utils.get_previous_awards(application, session)


@router.post(
    "/applications/find-alternative-credit-option",
    tags=["applications"],
    response_model=serializers.ApplicationResponse,
)
async def find_alternative_credit_option(
    payload: parsers.ApplicationBase,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(get_cognito_client),
):
    """
    Find an alternative credit option for a rejected application by copying it.

    :param payload: The payload containing the UUID of the rejected application.
    :type payload: parsers.ApplicationBase

    :param session: The database session.
    :type session: Session

    :param client: The Cognito client for sending notifications.
    :type client: CognitoClient

    :return: The newly created application as an alternative credit option.
    :rtype: serializers.ApplicationResponse

    :raise: HTTPException with status code 400 if the application has already been copied.
    :raise: HTTPException with status code 400 if the application is not in the rejected status.

    """
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)
        utils.check_if_application_was_already_copied(application, session)
        utils.check_application_status(application, models.ApplicationStatus.REJECTED)
        new_application = utils.copy_application(application, session)
        message_id = client.send_copied_application_notifications(new_application)

        utils.create_message(new_application, models.MessageType.APPLICATION_COPIED, session, message_id)

        utils.create_application_action(
            session,
            None,
            application.id,
            models.ApplicationActionType.COPIED_APPLICATION,
            payload,
        )
        utils.create_application_action(
            session,
            None,
            new_application.id,
            models.ApplicationActionType.APPLICATION_COPIED_FROM,
            payload,
        )

        return serializers.ApplicationResponse(
            application=new_application,
            borrower=new_application.borrower,
            award=new_application.award,
        )
