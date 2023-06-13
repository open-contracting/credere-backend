from datetime import datetime
from typing import List

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session, defaultload

from ..schema.core import Application, ApplicationStatus

excluded_applications = [
    ApplicationStatus.PENDING,
    ApplicationStatus.REJECTED,
    ApplicationStatus.LAPSED,
    ApplicationStatus.DECLINED,
]

OCP_can_modify = []


def update_application(
    application_id: int, payload: dict, session: Session
) -> Application:
    application = (
        session.query(Application).filter(Application.id == application_id).first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if application.status == ApplicationStatus.APPROVED:
        raise HTTPException(
            status_code=409, detail="Approved applications cannot be updated"
        )

    update_dict = jsonable_encoder(payload)
    for field, value in update_dict.items():
        setattr(application, field, value)

    session.add(application)
    session.commit()
    session.refresh(application)

    return application


def get_all_active_applications(
    page: int, page_size: int, session: Session
) -> List[Application]:
    applications = (
        session.query(Application)
        .filter(Application.status.notin_(excluded_applications))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return applications


def get_application_by_uuid(uuid: str, session: Session):
    application = (
        session.query(Application)
        .options(defaultload(Application.borrower), defaultload(Application.award))
        .filter(Application.uuid == uuid)
        .first()
    )

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
        )

    return application


def check_is_application_expired(application: Application):
    expired_at = application.expired_at

    current_time = datetime.now(expired_at.tzinfo)

    if application.expired_at < current_time:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Application expired",
        )


def check_application_status(
    application: Application, applicationStatus: ApplicationStatus
):
    if application.status != applicationStatus:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Application status is not {}".format(applicationStatus.name),
        )
