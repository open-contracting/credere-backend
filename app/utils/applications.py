from datetime import datetime

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session, defaultload, joinedload
from sqlalchemy import desc, asc

from app.schema.api import Pagination

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


def update_models(payload, model):
    update_dict = jsonable_encoder(payload, exclude_unset=True)
    for field, value in update_dict.items():
        setattr(model, field, value)


def update_models_with_validation(payload, model):
    update_dict = jsonable_encoder(payload, exclude_unset=True)
    for field, value in update_dict.items():
        if model.missing_data[field]:
            setattr(model, field, value)
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="This column cannot be updated",
            )


def create_application_action(
    session: Session,
    user_id: int,
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

    if application.status == core.ApplicationStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approved applications cannot be updated",
        )

    if user.is_OCP() and application.status not in OCP_can_modify:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This application cannot be updated by OCP Admins",
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

    if application.status == core.ApplicationStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approved applications cannot be updated",
        )

    if user.is_OCP() and application.status not in OCP_can_modify:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This application cannot be updated by OCP Admins",
        )

    update_models_with_validation(payload, application.award)

    session.add(application)
    session.flush()

    return application


from sqlalchemy import text


def get_all_active_applications(
    page: int, page_size: int, sort_field: str, sort_order: str, session: Session
) -> Pagination:
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

    applications = (
        applications_query.offset((page - 1) * page_size).limit(page_size).all()
    )

    return Pagination(
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
) -> Pagination:
    # applications_query = session.query(core.Application).filter(
    #     core.Application.lender_id == lender_id
    # )
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

    applications = (
        applications_query.offset((page - 1) * page_size).limit(page_size).all()
    )

    return Pagination(
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
