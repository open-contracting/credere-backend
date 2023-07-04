import logging

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.schema.api import UserListResponse

from ..schema import core
from .general_utils import update_models


def get_all_users(session: Session) -> UserListResponse:
    users_query = session.query(core.User)

    total_count = users_query.count()

    users = users_query.all()

    return UserListResponse(
        items=users,
        count=total_count,
        page=0,
        page_size=total_count,
    )


def update_user(session: Session, payload: dict, user_id: int) -> core.User:
    try:
        user = session.query(core.User).filter(core.User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Lender not found"
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
