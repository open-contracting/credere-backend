from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import asc, desc, text
from sqlalchemy.orm import Session, defaultload, joinedload

from app.schema.api import ApplicationListResponse

from ..schema import core
from .general_utils import update_models, update_models_with_validation

excluded_applications = [
    # core.ApplicationStatus.PENDING,
    core.ApplicationStatus.REJECTED,
    core.ApplicationStatus.LAPSED,
    core.ApplicationStatus.DECLINED,
]

OCP_cannot_modify = [
    core.ApplicationStatus.LAPSED,
    core.ApplicationStatus.DECLINED,
    core.ApplicationStatus.APPROVED,
    core.ApplicationStatus.CONTRACT_UPLOADED,
    core.ApplicationStatus.COMPLETED,
    core.ApplicationStatus.REJECTED,
]


def get_calculator_data(payload: dict):
    calculator_fields = jsonable_encoder(payload, exclude_unset=True)
    calculator_fields.pop("uuid")
    calculator_fields.pop("credit_product_id")
    calculator_fields.pop("sector")

    return calculator_fields


def approve_application(application: core.Application, payload: dict):
    if application.status != core.ApplicationStatus.STARTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This application cannot be approved",
        )
    payload_dict = jsonable_encoder(payload, exclude_unset=True)
    application.lender_approved_data = payload_dict
    application.status = core.ApplicationStatus.APPROVED
    application.lender_approved_at = datetime.utcnow()


def create_application_action(
    session: Session,
    user_id: Optional[int],
    application_id: int,
    type: core.ApplicationAction,
    payload: dict,
) -> core.ApplicationAction:
    update_dict = jsonable_encoder(payload, exclude_unset=True)

    new_action = core.ApplicationAction(
        type=type,
        data=update_dict,
        application_id=application_id,
        user_id=user_id,
    )
    session.add(new_action)
    session.flush()

    return new_action


def update_application_borrower(
    session: Session, application_id: int, payload: dict, user: core.User
) -> core.Application:
    application = (
        session.query(core.Application)
        .filter(core.Application.id == application_id)
        .options(defaultload(core.Application.borrower))
        .first()
    )
    if not application or not application.borrower:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application or borrower not found",
        )

    check_application_not_status(
        application,
        OCP_cannot_modify,
    )

    if not user.is_OCP() and application.lender_id != user.lender_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This application is not owned by this lender",
        )

    update_models(payload, application.borrower)

    session.add(application)
    session.flush()

    return application


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application or award not found",
        )

    check_application_not_status(
        application,
        OCP_cannot_modify,
    )

    if not user.is_OCP() and application.lender_id != user.lender_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This application is not owned by this lender",
        )

    update_models_with_validation(payload, application.award)

    session.add(application)
    session.flush()

    return application


def get_all_active_applications(
    page: int, page_size: int, sort_field: str, sort_order: str, session: Session
) -> ApplicationListResponse:
    sort_direction = desc if sort_order.lower() == "desc" else asc

    applications_query = (
        session.query(core.Application)
        .join(core.Award)
        .join(core.Borrower)
        .options(
            joinedload(core.Application.award),
            joinedload(core.Application.borrower),
        )
        .filter(core.Application.status.notin_(excluded_applications))
        .order_by(text(f"{sort_field} {sort_direction.__name__}"))
    )

    total_count = applications_query.count()

    applications = applications_query.offset(page * page_size).limit(page_size).all()

    return ApplicationListResponse(
        items=applications,
        count=total_count,
        page=page,
        page_size=page_size,
    )


def get_all_FI_user_applications(
    page: int,
    page_size: int,
    sort_field: str,
    sort_order: str,
    session: Session,
    lender_id,
) -> ApplicationListResponse:
    sort_direction = desc if sort_order.lower() == "desc" else asc

    applications_query = (
        session.query(core.Application)
        .join(core.Award)
        .join(core.Borrower)
        .options(
            joinedload(core.Application.award),
            joinedload(core.Application.borrower),
        )
        .filter(
            core.Application.status.notin_(excluded_applications),
            core.Application.lender_id == lender_id,
        )
        .order_by(text(f"{sort_field} {sort_direction.__name__}"))
    )
    total_count = applications_query.count()

    applications = applications_query.offset(page * page_size).limit(page_size).all()

    return ApplicationListResponse(
        items=applications,
        count=total_count,
        page=page,
        page_size=page_size,
    )


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

    if not expired_at:
        return

    current_time = datetime.now(expired_at.tzinfo)

    if application.expired_at < current_time:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Application expired",
        )


def check_application_status(
    application: core.Application,
    applicationStatus: core.ApplicationStatus,
    detail: str = None,
):
    if application.status != applicationStatus:
        message = "Application status is not {}".format(applicationStatus.name)
        if detail:
            message = detail
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
        )


def check_application_not_status(
    application: core.Application,
    applicationStatus: List[core.ApplicationStatus],
    detail: str = None,
):
    if application.status in applicationStatus:
        message = "Application status is {}".format(application.status.name)
        if detail:
            message = detail
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
        )


def create_message(
    application: core.Application,
    payload: dict,
    type: core.MessageType,
    message_id: str,
    session: Session,
):
    new_message = core.Message(
        application_id=application.id,
        body=payload,
        lender_id=application.lender.id,
        type=core.MessageType.APPROVED_APPLICATION,
        external_message_id=message_id,
    )
    session.add(new_message)
    session.commit()
