import logging

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.schema.api import LenderListResponse

from ..schema import core
from .general_utils import update_models

logger = logging.getLogger(__name__)


def get_all_lenders(session: Session) -> LenderListResponse:
    """
    Retrieve all lenders from the database.

    :param session: The database session.
    :type session: Session

    :return: A response object containing all lenders, the total count of lenders,
             and the current page and page size (in this case, both are equal to the total count).
    :rtype: LenderListResponse
    """
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
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Lender already exists",
        )


def create_credit_product(
    session: Session, payload: dict, lender_id
) -> core.CreditProduct:
    """
    Create a new lender and associated credit products in the database.

    :param session: The database session.
    :type session: Session

    :param payload: A dictionary containing the data for the new lender
                    and optionally a list of credit products.
    :type payload: dict

    :return: The created lender instance.
    :rtype: core.Lender

    :raises HTTPException: If the lender already exists in the database.
    """
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
    """
    Update a lender in the database.

    :param session: The database session.
    :type session: Session

    :param payload: A dictionary containing the data to update the lender.
    :type payload: dict

    :param lender_id: The ID of the lender to update.
    :type lender_id: int

    :return: The updated lender instance.
    :rtype: core.Lender

    :raises HTTPException: If the lender with the given ID doesn't exist
                           or if a lender with the same details already exists.
    """
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
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Lender already exists",
        )


def update_credit_product(
    session: Session, payload: dict, credit_product_id: int
) -> core.CreditProduct:
    """
    Update a credit product in the database.

    :param session: The database session.
    :type session: Session

    :param payload: A dictionary containing the data to update the credit product.
    :type payload: dict

    :param credit_product_id: The ID of the credit product to update.
    :type credit_product_id: int

    :return: The updated credit product instance.
    :rtype: core.CreditProduct

    :raises HTTPException: If the credit product with the given ID doesn't exist.
    """
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
