import logging
from datetime import datetime

import fastapi
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session

import app.utils.applications as utils
from app.background_processes.background_utils import generate_uuid
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

router = fastapi.APIRouter()


@router.patch(
    "/applications/change-email",
    tags=["applications"],
    response_model=ApiSchema.ApplicationResponse,
)
async def change_email(
    payload: ChangeEmail,
    session: Session = fastapi.Depends(get_db),
    client: CognitoClient = fastapi.Depends(get_cognito_client),
):
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)

        borrower_uuid = generate_uuid(application.borrower.email)
        application.borrower.uuid = borrower_uuid
        application.pending_email_confirmation = True
        send_new_email_confirmation(
            client.ses,
            application.borrower.legal_name,
            payload.new_email,
            payload.old_email,
            borrower_uuid,
            application.uuid,
        )

        return ApiSchema.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
        )


@router.get(
    "/applications/confirm-email/{applicaton_uuid}/{borrower_uuid}/{email}",
    tags=["applications"],
    response_model=ApiSchema.ApplicationResponse,
)
async def confirm(
    applicaton_uuid: str,
    borrower_uuid: str,
    email: str,
    session: Session = fastapi.Depends(get_db),
):
    with transaction_session(session):
        application = utils.get_application_by_uuid(applicaton_uuid, session)

        if (
            application.borrower.uuid != borrower_uuid
            and not application.pending_email_confirmation
        ):
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
                detail="Not authorized to modify this application",
            )
        application.borrower.email = email
        application.primary_email = email
        application.pending_email_confirmation = False

        return ApiSchema.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
        )


def allowed_file(filename):
    allowed_extensions = {"png", "pdf", "jpeg"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


@router.post(
    "/applications/upload",
    tags=["applications"],
)
async def upload_file(
    uuid: str = fastapi.Form(...),
    type: str = fastapi.Form(...),
    file: fastapi.UploadFile = fastapi.File(...),
    session: Session = fastapi.Depends(get_db),
):
    with transaction_session(session):
        await utils.validate_file(file)

        application = utils.get_application_by_uuid(uuid, session)

        new_document = {
            "application_id": application.id,
            "type": type,
            "file": await file.read(),
            "name": "file_name",
        }

        db_obj = core.BorrowerDocument(**new_document)

        session.add(db_obj)

        return ApiSchema.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
        )


@router.put(
    "/applications/{application_id}/award",
    tags=["applications"],
    response_model=core.Application,
)
async def update_application_award(
    application_id: int,
    payload: ApiSchema.AwardUpdate,
    user: core.User = fastapi.Depends(get_user),
    session: Session = fastapi.Depends(get_db),
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
    response_model=ApiSchema.ApplicationResponse,
)
async def update_application_borrower(
    application_id: int,
    payload: ApiSchema.BorrowerUpdate,
    user: core.User = fastapi.Depends(get_user),
    session: Session = fastapi.Depends(get_db),
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
        return ApiSchema.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
        )


@router.get(
    "/applications/admin-list",
    tags=["applications"],
    response_model=ApiSchema.ApplicationListResponse,
)
@OCP_only()
async def get_applications_list(
    page: int = fastapi.Query(0, ge=0),
    page_size: int = fastapi.Query(10, gt=0),
    sort_field: str = fastapi.Query("application.created_at"),
    sort_order: str = fastapi.Query("asc", regex="^(asc|desc)$"),
    current_user: core.User = fastapi.Depends(get_current_user),
    session: Session = fastapi.Depends(get_db),
):
    return utils.get_all_active_applications(
        page, page_size, sort_field, sort_order, session
    )


@router.get(
    "/applications/id/{id}",
    tags=["applications"],
    response_model=ApiSchema.ApplicationResponse,
)
@OCP_only()
async def get_application(
    id: int,
    current_user: str = fastapi.Depends(get_current_user),
    session: Session = fastapi.Depends(get_db),
):
    application = (
        session.query(core.Application).filter(core.Application.id == id).first()
    )

    return ApiSchema.ApplicationResponse(
        application=application, borrower=application.borrower, award=application.award
    )


@router.get(
    "/applications",
    tags=["applications"],
    response_model=ApiSchema.ApplicationListResponse,
)
async def get_applications(
    page: int = fastapi.Query(0, ge=0),
    page_size: int = fastapi.Query(10, gt=0),
    sort_field: str = fastapi.Query("application.created_at"),
    sort_order: str = fastapi.Query("asc", regex="^(asc|desc)$"),
    user: core.User = fastapi.Depends(get_user),
    session: Session = fastapi.Depends(get_db),
):
    return utils.get_all_FI_user_applications(
        page, page_size, sort_field, sort_order, session, user.lender_id
    )


@router.get(
    "/applications/uuid/{uuid}",
    tags=["applications"],
    response_model=ApiSchema.ApplicationResponse,
)
async def application_by_uuid(uuid: str, session: Session = fastapi.Depends(get_db)):
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
    background_tasks: fastapi.BackgroundTasks,
    session: Session = fastapi.Depends(get_db),
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
    session: Session = fastapi.Depends(get_db),
    client: CognitoClient = fastapi.Depends(get_cognito_client),
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
            return "error"


@router.post(
    "/applications/decline",
    tags=["applications"],
    response_model=ApiSchema.ApplicationResponse,
)
async def decline(
    payload: ApiSchema.ApplicationDeclinePayload,
    session: Session = fastapi.Depends(get_db),
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
    session: Session = fastapi.Depends(get_db),
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
    session: Session = fastapi.Depends(get_db),
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
