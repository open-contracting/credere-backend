from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models
from app.db import get_db
from app.settings import app_settings

router = APIRouter()


class UpdateApplicationStatus(BaseModel):
    status: models.ApplicationStatus


@router.get(
    "/set-test-application-as-lapsed/id/{id}",
    tags=["applications"],
    response_model=models.Application,
)
async def set_test_application_as_lapsed(id: int, session: Session = Depends(get_db)):
    application = session.query(models.Application).filter(models.Application.id == id).first()
    application.created_at = datetime.now(application.created_at.tzinfo) - timedelta(
        days=app_settings.days_to_change_to_lapsed + 2
    )

    session.commit()
    session.refresh(application)

    return application


@router.get(
    "/set-test-application-as-dated/id/{id}",
    tags=["applications"],
    response_model=models.Application,
)
async def set_test_application_as_dated(id: int, session: Session = Depends(get_db)):
    application = session.query(models.Application).filter(models.Application.id == id).first()
    application.borrower_declined_at = datetime.now(application.created_at.tzinfo) - timedelta(
        days=app_settings.days_to_erase_borrowers_data + 1
    )

    session.commit()
    session.refresh(application)

    return application


@router.get(
    "/set-application-as-started/id/{id}",
    tags=["applications"],
    response_model=models.Application,
)
async def set_test_application_as_started(id: int, session: Session = Depends(get_db)):
    application = session.query(models.Application).filter(models.Application.id == id).first()

    application.lender_started_at = datetime.now(application.created_at.tzinfo)
    application.status = models.ApplicationStatus.STARTED

    session.commit()
    session.refresh(application)

    return application


@router.get(
    "/set-application-as-overdue/id/{id}",
    tags=["applications"],
    response_model=models.Application,
)
async def set_test_application_as_overdue(id: int, session: Session = Depends(get_db)):
    application = session.query(models.Application).filter(models.Application.id == id).first()

    application.status = models.ApplicationStatus.STARTED
    application.lender_started_at = datetime.now(application.created_at.tzinfo) - timedelta(
        days=application.lender.sla_days + 1
    )

    session.commit()
    session.refresh(application)

    return application


@router.get(
    "/set-test-application-to-remind/id/{id}",
    tags=["applications"],
    response_model=models.Application,
)
async def set_test_application_to_remind(id: int, session: Session = Depends(get_db)):
    application = session.query(models.Application).filter(models.Application.id == id).first()
    application.expired_at = datetime.now(application.created_at.tzinfo) + timedelta(days=1)

    session.commit()
    session.refresh(application)

    return application


@router.get(
    "/set-test-application-to-remind-submit/id/{id}",
    tags=["applications"],
    response_model=models.Application,
)
async def set_test_application_to_remind_submit(id: int, session: Session = Depends(get_db)):
    application = session.query(models.Application).filter(models.Application.id == id).first()
    application.borrower_accepted_at = datetime.now(application.created_at.tzinfo) - timedelta(
        days=app_settings.days_to_change_to_lapsed - app_settings.reminder_days_before_lapsed
    )

    session.commit()
    session.refresh(application)

    return application


@router.post(
    "/applications/{id}/update-test-application-status",
    tags=["applications"],
    response_model=models.Application,
)
async def update_test_application_status(
    id: int, payload: UpdateApplicationStatus, session: Session = Depends(get_db)
):
    application = session.query(models.Application).filter(models.Application.id == id).first()
    application.status = payload.status

    session.commit()
    return application
