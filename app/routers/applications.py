import logging
from datetime import datetime

from botocore.exceptions import ClientError
from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

import app.utils.applications as utils
from app.background_processes.fetcher import fetch_previous_awards
from app.core.settings import app_settings
from app.schema import api as ApiSchema

from ..core.user_dependencies import CognitoClient, get_cognito_client
from ..db.session import get_db, transaction_session
from ..schema import core
from ..utils.permissions import OCP_only
from ..utils.verify_token import get_current_user, get_user

from fastapi import Depends, Query, status  # isort:skip # noqa
from fastapi import APIRouter, BackgroundTasks, HTTPException  # isort:skip # noqa

router = APIRouter()


@router.post(
    "/applications/{id}/approve",
    tags=["applications"],
    response_model=core.ApplicationWithRelations,
)
async def send_email(
    id: int,
    payload: ApiSchema.LenderApprovedData,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(get_cognito_client),
    user: core.User = Depends(get_user),
):
    with transaction_session(session):
        # this should be get application by id after merging 102 in dev
        application = (
            session.query(core.Application).filter(core.Application.id == id).first()
        )

        # before this I need to check if lender is assigned to application, function is also in branch 102

        application.lender_approved_data = payload
        application.status = core.ApplicationStatus.APPROVED

        utils.create_application_action(
            session,
            user.id,
            application.id,
            core.ApplicationActionType.APPROVED_APPLICATION,
            payload,
        )

        message_id = client.send_application_approved_to_sme(application)
        utils.create_message(
            application,
            payload,
            core.MessageType.APPROVED_APPLICATION,
            message_id,
            session,
        )

        return application


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

        return application


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
