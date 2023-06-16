from sqlalchemy.orm import Session

from app.schema.api import LenderPagination

from ..schema import core
from .general_utils import update_models


def get_all_lenders(page: int, page_size: int, session: Session) -> LenderPagination:
    lenders_query = session.query(core.Lender)

    total_count = lenders_query.count()

    lenders = lenders_query.offset((page - 1) * page_size).limit(page_size).all()

    return LenderPagination(
        items=lenders,
        count=total_count,
        page=page,
        page_size=page_size,
    )


def create_lender(session: Session, payload: dict, user: core.User) -> core.Lender:
    lender = core.Lender(**payload.dict())
    lender.users.append(user)

    session.add(lender)
    session.flush()

    return lender


def update_lender(session: Session, payload: dict, lender_id: int) -> core.Lender:
    lender = session.query(core.Lender).filter(core.Lender.id == lender_id).first()

    update_models(payload, lender)

    session.add(lender)
    session.flush()

    return lender
