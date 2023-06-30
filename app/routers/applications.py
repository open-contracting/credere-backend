import logging
from datetime import datetime

from botocore.exceptions import ClientError
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

import app.utils.applications as utils
from app.background_processes.fetcher import fetch_previous_awards
from app.core.settings import app_settings
from app.schema import api as ApiSchema
from app.schema.api import ChangeEmail
from app.utils.email_utility import send_new_email_confirmation

from ..core.user_dependencies import CognitoClient, get_cognito_client
from ..db.session import get_db, transaction_session
from ..schema import core
from ..utils.permissions import OCP_only
from ..utils.verify_token import get_current_user, get_user

from fastapi import Depends, Query, status  # isort:skip # noqa
from fastapi import Form, UploadFile  # isort:skip # noqa
from fastapi import APIRouter, BackgroundTasks, HTTPException  # isort:skip # noqa

router = APIRouter()


@router.patch(
    "/applications/change-email",
    tags=["applications"],
    response_model=core.ApplicationWithRelations,
)
async def change_email(
    payload: ChangeEmail,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(get_cognito_client),
):
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)

        confirmation_email_token = utils.update_application_primary_email(
            application, payload.new_email
        )
        utils.create_application_action(
            session,
            None,
            application.id,
            core.ApplicationActionType.MSME_CHANGE_EMAIL,
            payload,
        )
        external_message_id, body = send_new_email_confirmation(
            client.ses,
            application.borrower.legal_name,
            payload.new_email,
            payload.old_email,
            confirmation_email_token,
            application.uuid,
        )

        utils.create_message(
            application,
            core.MessageType.EMAIL_CHANGE_CONFIRMATION,
            session,
            external_message_id,
            body,
        )

        return application


@router.post(
    "/applications/confirm-email",
    tags=["applications"],
    response_model=core.ApplicationWithRelations,
)
async def confirm_email(
    payload: ApiSchema.ConfirmNewEmail,
    session: Session = Depends(get_db),
):
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)

        utils.check_pending_email_confirmation(
            application, payload.confirmation_email_token
        )

        utils.create_application_action(
            session,
            None,
            application.id,
            core.ApplicationActionType.MSME_CONFIRM_EMAIL,
            payload,
        )

        return application


@router.get(
    "/applications/documents/id/{id}",
    tags=["applications"],
)
async def get_borrower_document(
    id: int,
    session: Session = Depends(get_db),
    user: core.User = Depends(get_user),
):
    with transaction_session(session):
        document = (
            session.query(core.BorrowerDocument)
            .filter(core.BorrowerDocument.id == id)
            .first()
        )
        utils.get_file(document, user, session)

        def file_generator():
            yield document.file

        return StreamingResponse(
            file_generator(), media_type="application/octet-stream"
        )


@router.post(
    "/applications/upload-document",
    tags=["applications"],
    response_model=core.ApplicationWithRelations,
)
async def upload_document(
    file: UploadFile,
    uuid: str = Form(...),
    type: str = Form(...),
    session: Session = Depends(get_db),
):
    with transaction_session(session):
        new_file, filename = utils.validate_file(file)
        application = utils.get_application_by_uuid(uuid, session)

        utils.create_or_update_borrower_document(
            filename, application, type, session, new_file
        )

        utils.create_application_action(
            session,
            None,
            application.id,
            core.ApplicationActionType.MSME_UPLOAD_DOCUMENT,
            {"file_name": filename},
        )

        return application


@router.post(
    "/applications/upload-contract",
    tags=["applications"],
    response_model=core.ApplicationWithRelations,
)
async def upload_contract(
    file: UploadFile,
    uuid: str = Form(...),
    type: str = Form(...),
    session: Session = Depends(get_db),
):
    with transaction_session(session):
        new_file, filename = utils.validate_file(file)
        application = utils.get_application_by_uuid(uuid, session)

        utils.create_or_update_borrower_document(
            filename, application, type, session, new_file
        )

        utils.create_application_action(
            session,
            None,
            application.id,
            core.ApplicationActionType.MSME_UPLOAD_DOCUMENT,
            {"file_name": filename},
        )

        return application


@router.post(
    "/applications/{id}/upload-compliance",
    tags=["applications"],
    response_model=ApiSchema.ApplicationResponse,
)
async def upload_compliance(
    id: int,
    file: UploadFile,
    session: Session = Depends(get_db),
    user: core.User = Depends(get_user),
):
    with transaction_session(session):
        new_file, filename = utils.validate_file(file)
        application = utils.get_application_by_id(id, session)

        utils.check_FI_user_permission(application, user)

        utils.create_or_update_borrower_document(
            filename,
            application,
            core.BorrowerDocumentType.COMPLIANCE_REPORT,
            session,
            new_file,
        )

        utils.create_application_action(
            session,
            None,
            application.id,
            core.ApplicationActionType.FI_UPLOAD_COMPLIANCE,
            {"file_name": filename},
        )

        return ApiSchema.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
        )


@router.put(
    "/applications/verify-data-field",
    tags=["applications"],
    response_model=ApiSchema.ApplicationResponse,
)
async def verify_data_field(
    payload: ApiSchema.VerifyDataField,
    session: Session = Depends(get_db),
    user: core.User = Depends(get_user),
):
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)
        utils.check_FI_user_permission(application, user)
        utils.veify_data_field(application, payload.field)

        utils.create_application_action(
            session,
            user.id,
            application.id,
            core.ApplicationActionType.DATA_VALIDATION_UPDATE,
            payload,
        )

        return ApiSchema.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
        )


@router.post(
    "/applications/documents/{document_id}/verify-document",
    tags=["applications"],
    response_model=ApiSchema.ApplicationResponse,
)
async def verify_document(
    payload: ApiSchema.VerifyBorrowerDocument,
    session: Session = Depends(get_db),
    user: core.User = Depends(get_user),
):
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)
        utils.check_FI_user_permission(application, user)
        utils.verify_document(payload.document_id, session)

        utils.create_application_action(
            session,
            user.id,
            application.id,
            core.ApplicationActionType.BORROWER_DOCUMENT_UPDATE,
            payload,
        )

        return ApiSchema.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
        )


@router.put(
    "/applications/{application_id}/award",
    tags=["applications"],
    response_model=core.ApplicationWithRelations,
)
async def update_application_award(
    application_id: int,
    payload: ApiSchema.AwardUpdate,
    user: core.User = Depends(get_user),
    session: Session = Depends(get_db),
):
    with transaction_session(session):
        application = utils.update_application_award(
            session, application_id, payload, user
        )
        utils.create_application_action(
            session,
            user.id,
            application_id,
            core.ApplicationActionType.AWARD_UPDATE,
            payload,
        )

        return ApiSchema.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
        )


@router.put(
    "/applications/{application_id}/borrower",
    tags=["applications"],
    response_model=core.ApplicationWithRelations,
)
async def update_application_borrower(
    application_id: int,
    payload: ApiSchema.BorrowerUpdate,
    user: core.User = Depends(get_user),
    session: Session = Depends(get_db),
):
    with transaction_session(session):
        application = utils.update_application_borrower(
            session, application_id, payload, user
        )

        utils.create_application_action(
            session,
            user.id,
            application_id,
            core.ApplicationActionType.BORROWER_UPDATE,
            payload,
        )

        return application


@router.get(
    "/applications/admin-list",
    tags=["applications"],
    response_model=ApiSchema.ApplicationListResponse,
)
@OCP_only()
async def get_applications_list(
    page: int = Query(0, ge=0),
    page_size: int = Query(10, gt=0),
    sort_field: str = Query("application.created_at"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: core.User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    return utils.get_all_active_applications(
        page, page_size, sort_field, sort_order, session
    )


@router.get(
    "/applications/id/{id}",
    tags=["applications"],
    response_model=core.ApplicationWithRelations,
)
@OCP_only()
async def get_application(
    id: int,
    current_user: str = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    application = (
        session.query(core.Application).filter(core.Application.id == id).first()
    )

    return application


@router.get(
    "/applications",
    tags=["applications"],
    response_model=ApiSchema.ApplicationListResponse,
)
async def get_applications(
    page: int = Query(0, ge=0),
    page_size: int = Query(10, gt=0),
    sort_field: str = Query("application.created_at"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    user: core.User = Depends(get_user),
    session: Session = Depends(get_db),
):
    return utils.get_all_FI_user_applications(
        page, page_size, sort_field, sort_order, session, user.lender_id
    )


@router.get(
    "/applications/uuid/{uuid}",
    tags=["applications"],
    response_model=ApiSchema.ApplicationResponse,
)
async def application_by_uuid(uuid: str, session: Session = Depends(get_db)):
    application = utils.get_application_by_uuid(uuid, session)
    utils.check_is_application_expired(application)

    return ApiSchema.ApplicationResponse(
        application=application, borrower=application.borrower, award=application.award
    )


@router.post(
    "/applications/access-scheme",
    tags=["applications"],
    response_model=ApiSchema.ApplicationResponse,
)
async def access_scheme(
    payload: ApiSchema.ApplicationBase,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
):
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)
        utils.check_is_application_expired(application)
        utils.check_application_status(application, core.ApplicationStatus.PENDING)

        current_time = datetime.now(application.created_at.tzinfo)
        application.borrower_accepted_at = current_time
        application.status = core.ApplicationStatus.ACCEPTED
        application.expired_at = None

        background_tasks.add_task(fetch_previous_awards, application.borrower)

        return ApiSchema.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
        )


@router.post(
    "/applications/submit",
    tags=["applications"],
    response_model=ApiSchema.ApplicationResponse,
)
async def update_apps_send_notifications(
    payload: ApiSchema.ApplicationSubmit,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(get_cognito_client),
):
    with transaction_session(session):
        try:
            application = utils.get_application_by_uuid(payload.uuid, session)
            application.status = core.ApplicationStatus.SUBMITTED
            application.lender_id = payload.lender_id
            lender = (
                session.query(core.Lender)
                .filter(core.Lender.id == payload.lender_id)
                .first()
            )
            lender_name = lender.name
            lender_email_group = lender.email_group
            ocp_email_group = app_settings.ocp_email_group
            client.send_notifications_of_new_applications(
                ocp_email_group, lender_name, lender_email_group
            )
            return ApiSchema.ApplicationResponse(
                application=application,
                borrower=application.borrower,
                award=application.award,
            )
        except ClientError as e:
            logging.error(e)
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="There was an error",
            )


@router.post(
    "/applications/email-sme/{id}",
    tags=["applications"],
    response_model=ApiSchema.ApplicationResponse,
)
async def email_sme(
    id: int,
    payload: ApiSchema.ApplicationEmailSme,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(get_cognito_client),
    user: core.User = Depends(get_user),
):
    with transaction_session(session):
        try:
            application = (
                session.query(core.Application)
                .filter(core.Application.id == id)
                .first()
            )
            # Obtaing the lenderId from the user
            lender = (
                session.query(core.Lender)
                .filter(core.Lender.id == user.lender_id)
                .first()
            )
            application.status = core.ApplicationStatus.INFORMATION_REQUESTED
            current_time = datetime.now(application.created_at.tzinfo)
            application.information_requested_at = current_time

            message_id = client.send_request_to_sme(
                application.uuid,
                lender.name,
                payload.message,
                application.primary_email,
            )

            new_message = core.Message(
                application_id=application.id,
                body=payload.message,
                lender_id=lender.id,
                type=core.MessageType.FI_MESSAGE,
                external_message_id=message_id,
            )
            session.add(new_message)
            session.commit()

            return ApiSchema.ApplicationResponse(
                application=application,
                borrower=application.borrower,
                award=application.award,
            )
        except ClientError as e:
            logging.error(e)
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="There was an error",
            )


@router.post(
    "/applications/decline",
    tags=["applications"],
    response_model=ApiSchema.ApplicationResponse,
)
async def decline(
    payload: ApiSchema.ApplicationDeclinePayload,
    session: Session = Depends(get_db),
):
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)
        utils.check_is_application_expired(application)
        utils.check_application_status(application, core.ApplicationStatus.PENDING)

        borrower_declined_data = vars(payload)
        borrower_declined_data.pop("uuid")

        application.borrower_declined_data = borrower_declined_data
        application.status = core.ApplicationStatus.DECLINED
        current_time = datetime.now(application.created_at.tzinfo)
        application.borrower_declined_at = current_time

        if payload.decline_all:
            application.borrower.status = core.BorrowerStatus.DECLINE_OPPORTUNITIES
            application.borrower.declined_at = current_time

        return ApiSchema.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
        )


@router.post(
    "/applications/rollback-decline",
    tags=["applications"],
    response_model=ApiSchema.ApplicationResponse,
)
async def rollback_decline(
    payload: ApiSchema.ApplicationBase,
    session: Session = Depends(get_db),
):
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)
        utils.check_is_application_expired(application)
        utils.check_application_status(application, core.ApplicationStatus.DECLINED)

        application.borrower_declined_data = {}
        application.status = core.ApplicationStatus.PENDING
        application.borrower_declined_at = None

        if application.borrower.status == core.BorrowerStatus.DECLINE_OPPORTUNITIES:
            application.borrower.status = core.BorrowerStatus.ACTIVE
            application.borrower.declined_at = None

        return ApiSchema.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
        )


@router.post(
    "/applications/decline-feedback",
    tags=["applications"],
    response_model=ApiSchema.ApplicationResponse,
)
async def decline_feedback(
    payload: ApiSchema.ApplicationDeclineFeedbackPayload,
    session: Session = Depends(get_db),
):
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)
        utils.check_is_application_expired(application)
        utils.check_application_status(application, core.ApplicationStatus.DECLINED)

        borrower_declined_preferences_data = vars(payload)
        borrower_declined_preferences_data.pop("uuid")

        application.borrower_declined_preferences_data = (
            borrower_declined_preferences_data
        )

        return ApiSchema.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
        )
