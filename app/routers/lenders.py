from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

import app.utils.lenders as utils
from app.schema import api as ApiSchema

from ..db.session import get_db, transaction_session
from ..schema import core
from ..utils.permissions import OCP_only
from ..utils.verify_token import get_current_user

router = APIRouter()


@router.post(
    "/lenders",
    tags=["lenders"],
    response_model=core.Lender,
)
@OCP_only()
async def create_lender(
    lender: core.LenderCreate,
    current_user: core.User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """
    Create a new lender.

    :param lender: The lender data to be created.
    :type lender: core.LenderCreate

    :param current_user: The current user authenticated.
    :type current_user: core.User

    :param session: The database session.
    :type session: Session

    :return: The created lender.
    :rtype: core.Lender

    :raise: lumache.OCPOnlyError if the current user is not authorized.
    """
    with transaction_session(session):
        return utils.create_lender(session, lender)


@router.post(
    "/lenders/{lender_id}/credit-products",
    tags=["lenders"],
    response_model=core.CreditProduct,
)
@OCP_only()
async def create_credit_products(
    credit_product: core.CreditProduct,
    lender_id: int,
    current_user: core.User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """
    Create a new credit product for a specific lender.

    :param credit_product: The credit product data to be created.
    :type credit_product: core.CreditProduct

    :param lender_id: The ID of the lender for which the credit product will be created.
    :type lender_id: int

    :param current_user: The current user authenticated.
    :type current_user: core.User

    :param session: The database session.
    :type session: Session

    :return: The created credit product.
    :rtype: core.CreditProduct

    :raise: lumache.OCPOnlyError if the current user is not authorized.
    """
    with transaction_session(session):
        return utils.create_credit_product(session, credit_product, lender_id)


@router.get("/lenders/{lender_id}", tags=["lenders"], response_model=core.LenderWithRelations)
async def get_lender(lender_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a lender by its ID.

    :param lender_id: The ID of the lender to retrieve.
    :type lender_id: int

    :param db: The database session.
    :type db: Session

    :return: The lender with the specified ID.
    :rtype: core.LenderWithRelations

    :raise: HTTPException with status code 404 if the lender is not found.
    """
    lender = db.query(core.Lender).filter(core.Lender.id == lender_id).first()

    if not lender:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lender not found")
    return lender


@router.put(
    "/lenders/{id}",
    tags=["lenders"],
    response_model=core.Lender,
)
@OCP_only()
async def update_lender(
    id: int,
    payload: core.LenderBase,
    current_user: core.User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """
    Update an existing lender.

    :param id: The ID of the lender to update.
    :type id: int

    :param payload: The data to update the lender with.
    :type payload: core.LenderBase

    :param current_user: The current user authenticated.
    :type current_user: core.User

    :param session: The database session.
    :type session: Session

    :return: The updated lender.
    :rtype: core.Lender

    :raise: lumache.OCPOnlyError if the current user is not authorized.
    """
    with transaction_session(session):
        return utils.update_lender(session, payload, id)


@router.get(
    "/lenders",
    tags=["lenders"],
    response_model=ApiSchema.LenderListResponse,
)
async def get_lenders_list(
    session: Session = Depends(get_db),
):
    """
    Get the list of all lenders.

    :param session: The database session.
    :type session: Session

    :return: The list of all lenders.
    :rtype: ApiSchema.LenderListResponse
    """
    return utils.get_all_lenders(session)


@router.get(
    "/credit-products/{credit_product_id}",
    tags=["lenders"],
    response_model=core.CreditProductWithLender,
)
async def get_credit_product(
    credit_product_id: int,
    session: Session = Depends(get_db),
):
    """
    Retrieve a credit product by its ID, including its associated lender information.

    :param credit_product_id: The ID of the credit product to retrieve.
    :type credit_product_id: int

    :param session: The database session.
    :type session: Session

    :return: The credit product with the specified ID and its associated lender information.
    :rtype: core.CreditProductWithLender

    :raise: HTTPException with status code 404 if the credit product is not found.
    """
    creditProduct = (
        session.query(core.CreditProduct)
        .join(core.Lender)
        .options(joinedload(core.CreditProduct.lender))
        .filter(core.CreditProduct.id == credit_product_id)
        .first()
    )

    if not creditProduct:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credit product not found")

    return creditProduct


@router.put(
    "/credit-products/{credit_product_id}",
    tags=["lenders"],
    response_model=core.CreditProduct,
)
@OCP_only()
async def update_credit_products(
    credit_product: core.CreditProduct,
    credit_product_id: int,
    current_user: core.User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """
    Update an existing credit product.

    :param credit_product: The credit product data to update.
    :type credit_product: core.CreditProduct

    :param credit_product_id: The ID of the credit product to update.
    :type credit_product_id: int

    :param current_user: The current user authenticated.
    :type current_user: core.User

    :param session: The database session.
    :type session: Session

    :return: The updated credit product.
    :rtype: core.CreditProduct

    :raise: lumache.OCPOnlyError if the current user is not authorized.
    """
    with transaction_session(session):
        return utils.update_credit_product(session, credit_product, credit_product_id)
