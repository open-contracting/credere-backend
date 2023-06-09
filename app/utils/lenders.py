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
        # Create a Lender instance without the credit_product data
        lender = core.Lender(**payload.dict(exclude={"credit_products"}))
        session.add(lender)

        # Create a CreditProduct instance for each credit product and add it to the lender
        if payload.credit_products:
            for cp in payload.credit_products:
                credit_product = core.CreditProduct(**cp.dict(), lender=lender)
                session.add(credit_product)

        session.flush()

        return lender
    except IntegrityError as e:
        logging.error(e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Lender already exists",
        )


def create_credit_product(
    session: Session, payload: dict, lender_id
) -> core.CreditProduct:
    lender = session.query(core.Lender).filter(core.Lender.id == lender_id).first()
    if not lender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lender not found"
        )

    credit_product = core.CreditProduct(**payload.dict(), lender=lender)
    session.add(credit_product)
    session.flush()

    return credit_product


def update_lender(session: Session, payload: dict, lender_id: int) -> core.Lender:
    try:
        lender = session.query(core.Lender).filter(core.Lender.id == lender_id).first()
        if not lender:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Lender not found"
            )

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


def update_credit_product(
    session: Session, payload: dict, credit_product_id: int
) -> core.CreditProduct:
    credit_product = (
        session.query(core.CreditProduct)
        .filter(core.CreditProduct.id == credit_product_id)
        .first()
    )
    if not credit_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Credit product not found"
        )

    update_models(payload, credit_product)
    session.add(credit_product)
    session.flush()

    return credit_product
