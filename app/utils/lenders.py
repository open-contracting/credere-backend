import logging

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.schema.api import LenderListResponse

from ..schema import core
from .general_utils import update_models


def get_all_lenders(session: Session) -> LenderListResponse:
    lenders_query = session.query(core.Lender)

    total_count = lenders_query.count()

    lenders = lenders_query.all()

    return LenderListResponse(
        items=lenders,
        count=total_count,
        page=0,
        page_size=total_count,
    )


def create_lender(session: Session, payload: dict) -> core.Lender:
    try:
        lender = core.Lender(**payload.dict())

        session.add(lender)
        session.flush()

        return lender
    except IntegrityError as e:
        logging.error(e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Lender already exists",
        )


def update_lender(session: Session, payload: dict, lender_id: int) -> core.Lender:
    try:
        lender = session.query(core.Lender).filter(core.Lender.id == lender_id).first()
        update_models(payload, lender)

        session.add(lender)
        session.flush()

        return lender
    except IntegrityError as e:
        logging.error(e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Lender already exists",
        )
