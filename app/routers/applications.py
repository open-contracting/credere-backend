from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import app.utils.applications as utils
from app.schema import api as ApiSchema

from ..db.session import get_db, transaction_session
from ..schema.core import ApplicationStatus, BorrowerStatus

router = APIRouter()


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
    payload: ApiSchema.ApplicationBase, session: Session = Depends(get_db)
):
    with transaction_session(session):
        application = utils.get_application_by_uuid(payload.uuid, session)
        utils.check_is_application_expired(application)
        utils.check_application_status(application, ApplicationStatus.PENDING)

        current_time = datetime.now(application.created_at.tzinfo)
        application.borrower_accepted_at = current_time
        application.status = ApplicationStatus.ACCEPTED
        application.expired_at = None

        return ApiSchema.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
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
        utils.check_application_status(application, ApplicationStatus.PENDING)

        borrower_declined_data = vars(payload)
        borrower_declined_data.pop("uuid")

        application.borrower_declined_data = borrower_declined_data
        application.status = ApplicationStatus.DECLINED
        current_time = datetime.now(application.created_at.tzinfo)
        application.borrower_declined_at = current_time

        # delete borrower data
        application.borrower.legal_name = ""
        application.borrower.legal_identifier = ""
        application.borrower.email = ""
        application.borrower.address = ""
        application.borrower.declined_at = current_time

        if payload.decline_all:
            application.borrower.status = BorrowerStatus.DECLINE_OPPORTUNITIES

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
        utils.check_application_status(application, ApplicationStatus.DECLINED)

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
