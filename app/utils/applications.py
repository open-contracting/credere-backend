from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, defaultload

from ..schema.core import Application, ApplicationStatus


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

    if not expired_at:
        return

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
