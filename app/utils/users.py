import logging

from fastapi import HTTPException, status
from sqlalchemy import asc, desc, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.user_dependencies import CognitoClient
from app.db.session import transaction_session
from app.schema.api import UserListResponse

from ..schema import core
from .general_utils import update_models


def create_user(
    payload: core.User, session: Session, client: CognitoClient
) -> core.User:
    with transaction_session(session):
        try:
            user = core.User(**payload.dict())

            session.add(user)
            cognitoResponse = client.admin_create_user(payload.email, payload.name)
            user.external_id = cognitoResponse["User"]["Username"]

            return user
        except (client.exceptions().UsernameExistsException, IntegrityError) as e:
            logging.error(e)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Username already exists",
            )


def update_user(session: Session, payload: dict, user_id: int) -> core.User:
    try:
        user = session.query(core.User).filter(core.User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        update_models(payload, user)
        session.add(user)
        session.flush()

        return user
    except IntegrityError as e:
        logging.error(e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="User already exists",
        )


def get_all_users(
    page: int, page_size: int, sort_field: str, sort_order: str, session: Session
) -> UserListResponse:
    sort_direction = desc if sort_order.lower() == "desc" else asc

    list_query = (
        session.query(core.User)
        .outerjoin(core.Lender)
        .options(
            joinedload(core.User.lender),
        )
        .order_by(text(f"{sort_field} {sort_direction.__name__}"))
    )

    total_count = list_query.count()

    users = list_query.offset(page * page_size).limit(page_size).all()

    return UserListResponse(
        items=users,
        count=total_count,
        page=page,
        page_size=page_size,
    )
