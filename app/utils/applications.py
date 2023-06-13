from datetime import datetime
from typing import List

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session, defaultload

from ..schema import core

excluded_applications = [
    core.ApplicationStatus.PENDING,
    core.ApplicationStatus.REJECTED,
    core.ApplicationStatus.LAPSED,
    core.ApplicationStatus.DECLINED,
]

OCP_can_modify = [
    core.ApplicationStatus.PENDING,
    core.ApplicationStatus.ACCEPTED,
    core.ApplicationStatus.SUBMITTED,
    core.ApplicationStatus.INFORMATION_REQUESTED,
]


def create_application_action(
    session: Session,
    user_id: int,
    application_id: int,
    type: core.ApplicationAction,
    payload: dict,
) -> core.ApplicationAction:
    update_dict = jsonable_encoder(payload)

    new_action = core.ApplicationAction(
        type=type,
        data=update_dict,
        application_id=application_id,
        user_id=user_id,
    )
    session.add(new_action)
    session.commit()
    session.refresh(new_action)

    return new_action


def update_application_award(
    session: Session, application_id: int, payload: dict, user: core.User
) -> core.Application:
    application = (
        session.query(core.Application)
        .filter(core.Application.id == application_id)
        .options(defaultload(core.Application.award))
        .first()
    )
    if not application or not application.award:
        raise HTTPException(status_code=404, detail="Application or award not found")

    if application.status == core.ApplicationStatus.APPROVED:
        raise HTTPException(
            status_code=409, detail="Approved applications cannot be updated"
        )

    if user.is_OCP() and application.status not in OCP_can_modify:
        raise HTTPException(
            status_code=409, detail="This application cannot be updated by OCP Admins"
        )

    update_dict = jsonable_encoder(payload)
    for field, value in update_dict.items():
        setattr(application.award, field, value)

    session.add(application)
    session.refresh(application)

    return application


def get_all_active_applications(
    page: int, page_size: int, session: Session
) -> List[core.Application]:
    applications = (
        session.query(core.Application)
        .filter(core.Application.status.notin_(excluded_applications))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return applications


def get_application_by_uuid(uuid: str, session: Session):
    application = (
        session.query(core.Application)
        .options(
            defaultload(core.Application.borrower), defaultload(core.Application.award)
        )
        .filter(core.Application.uuid == uuid)
        .first()
    )

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
        )

    return application


def check_is_application_expired(application: core.Application):
    expired_at = application.expired_at

    current_time = datetime.now(expired_at.tzinfo)

    if application.expired_at < current_time:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Application expired",
        )


def check_application_status(
    application: core.Application, applicationStatus: core.ApplicationStatus
):
    if application.status != applicationStatus:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Application status is not {}".format(applicationStatus.name),
        )
