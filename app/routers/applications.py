from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, defaultload

from app.schema import api

from ..db.session import get_db
from ..schema.core import Application, ApplicationStatus

router = APIRouter()


@router.get(
    "/applications/uuid/{uuid}",
    tags=["applications"],
    response_model=api.ApplicationResponse,
)
async def get_application_by_uuid(uuid: str, session: Session = Depends(get_db)):
    application = (
        session.query(Application)
        .options(defaultload(Application.borrower), defaultload(Application.award))
        .filter(Application.uuid == uuid)
        .first()
    )
    expired_at = application.expired_at

    current_time = datetime.now(expired_at.tzinfo)

    if application.expired_at < current_time:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or uuid expired",
        )
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
        )
    return api.ApplicationResponse(
        application=application, borrower=application.borrower, award=application.award
    )


@router.post(
    "/applications/decline/",
    tags=["applications"],
    response_model=api.ApplicationResponse,
)
async def decline(
    payload: api.ApplicationDeclinePayload,
    session: Session = Depends(get_db),
):
    application = (
        session.query(Application)
        .options(defaultload(Application.borrower), defaultload(Application.award))
        .filter(Application.uuid == payload.uuid)
        .first()
    )
    expired_at = application.expired_at

    current_time = datetime.now(expired_at.tzinfo)

    if application.expired_at < current_time:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or uuid expired",
        )
    if application.status != ApplicationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application status is not pending",
        )

    application.borrower_declined_data = {
        "decline_this": payload.decline_this,
        "decline_all": payload.decline_all,
    }

    session.commit()
    return api.ApplicationResponse(
        application=application, borrower=application.borrower, award=application.award
    )


@router.post(
    "/applications/decline-feedback",
    tags=["applications"],
    response_model=api.ApplicationResponse,
)
async def decline_feedback(
    payload: api.ApplicationDeclineFeedbackPayload, session: Session = Depends(get_db)
):
    application = (
        session.query(Application)
        .options(defaultload(Application.borrower), defaultload(Application.award))
        .filter(Application.uuid == payload.uuid)
        .first()
    )
    expired_at = application.expired_at

    current_time = datetime.now(expired_at.tzinfo)

    if application.expired_at < current_time:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or uuid expired",
        )
    if application.status != ApplicationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or status is not pending",
        )

    application.borrower_declined_preferences_data = {
        "decline_this": payload.decline_this,
    }

    session.commit()
    return api.ApplicationResponse(
        application=application, borrower=application.borrower, award=application.award
    )
