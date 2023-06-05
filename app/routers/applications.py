from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, defaultload

from app.schema import api

from ..db.session import get_db
from ..schema.core import Application

router = APIRouter()


@router.get(
    "/applications/uuid/{uuid}",
    tags=["applications"],
    response_model=api.ApplicationResponse,
)
async def get_application_by_uuid(uuid: str, db: Session = Depends(get_db)):
    application = (
        db.query(Application)
        .options(defaultload(Application.borrower), defaultload(Application.award))
        .filter(Application.uuid == uuid)
        .first()
    )
    # validate not expired
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return api.ApplicationResponse(
        application=application, borrower=application.borrower, award=application.award
    )


@router.post(
    "/applications/decline",
    tags=["applications"],
    response_model=api.ApplicationResponse,
)
async def decline(
    payload: api.ApplicationDeclinePayload, db: Session = Depends(get_db)
):
    # validate is pending
    # update borrower_declined_data
    return None


@router.post(
    "/applications/decline-feedback",
    tags=["applications"],
    response_model=api.ApplicationResponse,
)
async def decline_feedback(
    payload: api.ApplicationDeclineFeedbackPayload, db: Session = Depends(get_db)
):
    # validate is pending
    # update borrower_declined_preferences_data
    return None
