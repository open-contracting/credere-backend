import logging
from datetime import datetime

from botocore.exceptions import ClientError
from fastapi.responses import StreamingResponse
from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

import app.utils.applications as utils
from app.background_processes.fetcher import fetch_previous_awards
from app.core.settings import app_settings
from app.schema import api as ApiSchema
from app.schema.api import ChangeEmail

from ..core.user_dependencies import CognitoClient, get_cognito_client
from ..db.session import get_db, transaction_session
from ..schema import core
from ..utils.permissions import OCP_only
from ..utils.verify_token import get_current_user, get_user

from fastapi import Depends, Query, status  # isort:skip # noqa
from fastapi import Form, UploadFile  # isort:skip # noqa
from fastapi import APIRouter, BackgroundTasks, HTTPException  # isort:skip # noqa

router = APIRouter()


@router.post(
    "/applications/{id}/reject-application",
    tags=["applications"],
    response_model=core.ApplicationWithRelations,
)
async def reject_application(
    id: int,
    payload: ApiSchema.LenderRejectedApplication,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(get_cognito_client),
    user: core.User = Depends(get_user),
):
    with transaction_session(session):
        application = utils.get_application_by_id(id, session)
        utils.check_FI_user_permission(application, user)
        utils.check_application_status(application, core.ApplicationStatus.STARTED)
        utils.reject_application(application, payload)
        utils.create_application_action(
            session,
            user.id,
            application.id,
            core.ApplicationActionType.REJECTED_APPLICATION,
            payload,
        )
        options = (
            session.query(core.CreditProduct)
            .join(core.Lender)
            .options(joinedload(core.CreditProduct.lender))
            .filter(
                and_(
                    core.CreditProduct.borrower_size == application.borrower.size,
                    core.CreditProduct.lender_id != application.lender_id,
                    core.CreditProduct.lower_limit <= application.amount_requested,
                    core.CreditProduct.upper_limit >= application.amount_requested,
                )
            )
            .all()
        )
        message_id = client.send_rejected_email_to_sme(application, options)
        utils.create_message(
            application, core.MessageType.REJECTED_APPLICATION, session, message_id
        )
        return application


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
        external_message_id = client.send_new_email_confirmation_to_sme(
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
    response_model=core.BorrowerDocumentBase,
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
        if not application.pending_documents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot upload document at this stage",
            )

        document = utils.create_or_update_borrower_document(
            filename, application, type, session, new_file
        )

        utils.create_application_action(
            session,
            None,
            application.id,
            core.ApplicationActionType.MSME_UPLOAD_DOCUMENT,
            {"file_name": filename},
        )

        return document


@router.post(
    "/applications/upload-contract",
    tags=["applications"],
    response_model=core.ApplicationWithRelations,
)
async def upload_contract(
    file: UploadFile,
    uuid: str = Form(...),
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(get_cognito_client),
):
    with transaction_session(session):
        new_file, filename = utils.validate_file(file)
        application = utils.get_application_by_uuid(uuid, session)

        utils.check_application_status(application, core.ApplicationStatus.APPROVED)

        utils.create_or_update_borrower_document(
            filename,
            application,
            core.BorrowerDocumentType.SIGNED_CONTRACT,
            session,
            new_file,
        )

        utils.create_application_action(
            session,
            None,
            application.id,
            core.ApplicationActionType.BORROWER_UPLOADED_CONTRACT,
            {"file_name": filename},
        )

        FI_message_id, SME_message_id = client.send_upload_contract_notifications(
            application
        )

        utils.create_message(
            application,
            core.MessageType.CONTRACT_UPLOAD_CONFIRMATION_TO_FI,
            session,
            FI_message_id,
        )

        utils.create_message(
            application,
            core.MessageType.CONTRACT_UPLOAD_CONFIRMATION,
            session,
            SME_message_id,
        )

        return application


@router.post(
    "/applications/{id}/upload-compliance",
    tags=["applications"],
    response_model=core.ApplicationWithRelations,
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

        return application


@router.put(
    "/applications/verify-data-field",
    tags=["applications"],
    response_model=core.ApplicationWithRelations,
)
async def verify_data_field(
    payload: ApiSchema.UpdateDataField,
    session: Session = Depends(get_db),
    user: core.User = Depends(get_user),
):
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)
        utils.check_FI_user_permission(application, user)
        utils.update_data_field(application, payload)

        utils.create_application_action(
            session,
            user.id,
            application.id,
            core.ApplicationActionType.DATA_VALIDATION_UPDATE,
            payload,
        )

        return application


@router.post(
    "/applications/documents/{document_id}/verify-document",
    tags=["applications"],
    response_model=core.ApplicationWithRelations,
)
async def verify_document(
    document_id: int,
    payload: ApiSchema.VerifyBorrowerDocument,
    session: Session = Depends(get_db),
    user: core.User = Depends(get_user),
):
    with transaction_session(session):
        document = utils.get_document_by_id(document_id, session)
        utils.check_FI_user_permission(document.application, user)

        document.verified = payload.verified

        utils.create_application_action(
            session,
            user.id,
            document.application.id,
            core.ApplicationActionType.BORROWER_DOCUMENT_UPDATE,
            payload,
        )

        return document.application


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
async def get_application(
    id: int,
    user: core.User = Depends(get_user),
    session: Session = Depends(get_db),
):
    application = (
        session.query(core.Application).filter(core.Application.id == id).first()
    )

    if user.is_OCP:
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
    response_model=core.ApplicationWithRelations,
)
async def start_application(
    id: int,
    user: core.User = Depends(get_user),
    session: Session = Depends(get_db),
):
    with transaction_session(session):
        application = (
            session.query(core.Application).filter(core.Application.id == id).first()
        )
        utils.check_application_status(application, core.ApplicationStatus.SUBMITTED)

        if user.lender_id != application.lender_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized to start this application",
            )

        application.status = core.ApplicationStatus.STARTED
        application.lender_started_at = datetime.now(application.created_at.tzinfo)
        # TODO add action

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
        application=application,
        borrower=application.borrower,
        award=application.award,
        lender=application.lender,
        documents=application.borrower_documents,
        creditProduct=application.creditProduct,
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
    "/applications/credit-product-options",
    tags=["applications"],
    response_model=ApiSchema.CreditProductListResponse,
)
async def credit_product_options(
    payload: ApiSchema.ApplicationCreditOptions,
    session: Session = Depends(get_db),
):
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)
        utils.check_is_application_expired(application)
        utils.check_application_status(application, core.ApplicationStatus.ACCEPTED)

        loans = (
            session.query(core.CreditProduct)
            .join(core.Lender)
            .options(joinedload(core.CreditProduct.lender))
            .filter(
                and_(
                    core.CreditProduct.type == core.CreditType.LOAN,
                    core.CreditProduct.borrower_size == payload.borrower_size,
                    core.CreditProduct.lower_limit <= payload.amount_requested,
                    core.CreditProduct.upper_limit >= payload.amount_requested,
                )
            )
            .all()
        )

        credit_lines = (
            session.query(core.CreditProduct)
            .join(core.Lender)
            .options(joinedload(core.CreditProduct.lender))
            .filter(
                and_(
                    core.CreditProduct.type == core.CreditType.CREDIT_LINE,
                    core.CreditProduct.borrower_size == payload.borrower_size,
                    core.CreditProduct.lower_limit <= payload.amount_requested,
                    core.CreditProduct.upper_limit >= payload.amount_requested,
                )
            )
            .all()
        )

        return ApiSchema.CreditProductListResponse(
            loans=loans, credit_lines=credit_lines
        )


@router.post(
    "/applications/select-credit-product",
    tags=["applications"],
    response_model=ApiSchema.ApplicationResponse,
)
async def select_credit_product(
    payload: ApiSchema.ApplicationSelectCreditProduct,
    session: Session = Depends(get_db),
):
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)
        utils.check_is_application_expired(application)
        utils.check_application_status(application, core.ApplicationStatus.ACCEPTED)

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
            core.ApplicationActionType.APPLICATION_CALCULATOR_DATA_UPDATE,
            payload,
        )

        return ApiSchema.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
        )


@router.post(
    "/applications/rollback-select-credit-product",
    tags=["applications"],
    response_model=ApiSchema.ApplicationResponse,
)
async def rollback_select_credit_product(
    payload: ApiSchema.ApplicationBase,
    session: Session = Depends(get_db),
):
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)
        utils.check_is_application_expired(application)
        utils.check_application_status(application, core.ApplicationStatus.ACCEPTED)

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

        return ApiSchema.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
        )


@router.post(
    "/applications/confirm-credit-product",
    tags=["applications"],
    response_model=ApiSchema.ApplicationResponse,
)
async def confirm_credit_product(
    payload: ApiSchema.ApplicationBase,
    session: Session = Depends(get_db),
):
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)
        utils.check_is_application_expired(application)
        utils.check_application_status(application, core.ApplicationStatus.ACCEPTED)

        if not application.credit_product_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credit product not selected",
            )

        creditProduct = (
            session.query(core.CreditProduct)
            .filter(core.CreditProduct.id == application.credit_product_id)
            .first()
        )

        if not creditProduct:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credit product not found",
            )

        application.lender_id = creditProduct.lender_id
        application.amount_requested = application.calculator_data.get(
            "amount_requested", None
        )
        application.repayment_years = application.calculator_data.get(
            "repayment_years", None
        )
        application.repayment_months = application.calculator_data.get(
            "repayment_months", None
        )
        application.payment_start_date = application.calculator_data.get(
            "payment_start_date", None
        )

        application.pending_documents = True

        utils.create_application_action(
            session,
            None,
            application.id,
            core.ApplicationActionType.APPLICATION_CONFIRM_CREDIT_PRODUCT,
            {},
        )

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
    payload: ApiSchema.ApplicationBase,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(get_cognito_client),
):
    with transaction_session(session):
        try:
            application = utils.get_application_by_uuid(payload.uuid, session)
            utils.check_application_status(application, core.ApplicationStatus.ACCEPTED)

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

            application.status = core.ApplicationStatus.SUBMITTED
            current_time = datetime.now(application.created_at.tzinfo)
            application.borrower_submitted_at = current_time
            application.pending_documents = False

            client.send_notifications_of_new_applications(
                ocp_email_group=app_settings.ocp_email_group,
                lender_name=application.lender.name,
                lender_email_group=application.lender.email_group,
            )

            return ApiSchema.ApplicationResponse(
                application=application,
                borrower=application.borrower,
                award=application.award,
                lender=application.lender,
            )
        except ClientError as e:
            logging.error(e)
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="There was an error submiting the application",
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
