import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app import dependencies, models, serializers
from app.db import get_db, transaction_session
from app.util import get_object_or_404

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post(
    "/lenders",
    tags=["lenders"],
)
async def create_lender(
    lender: models.LenderCreate,
    admin: models.User = Depends(dependencies.get_admin_user),
    session: Session = Depends(get_db),
) -> models.Lender:
    """
    Create a new lender.

    :param lender: The lender data to be created.
    :return: The created lender.
    :raise: lumache.OCPOnlyError if the current user is not authorized.
    """
    # Rename query parameter.
    payload = lender

    with transaction_session(session):
        try:
            # Create a Lender instance without the credit_product data
            lender = models.Lender(**payload.dict(exclude={"credit_products"}))
            session.add(lender)

            # Create a CreditProduct instance for each credit product and add it to the lender
            if payload.credit_products:
                for cp in payload.credit_products:
                    credit_product = models.CreditProduct(**cp.dict(), lender=lender)
                    session.add(credit_product)

            session.flush()
            return lender
        except IntegrityError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Lender already exists",
            )


@router.post(
    "/lenders/{lender_id}/credit-products",
    tags=["lenders"],
)
async def create_credit_products(
    credit_product: models.CreditProduct,
    lender_id: int,
    admin: models.User = Depends(dependencies.get_admin_user),
    session: Session = Depends(get_db),
) -> models.CreditProduct:
    """
    Create a new credit product for a specific lender.

    :param credit_product: The credit product data to be created.
    :param lender_id: The ID of the lender for which the credit product will be created.
    :return: The created credit product.
    :raise: lumache.OCPOnlyError if the current user is not authorized.
    """
    with transaction_session(session):
        lender = get_object_or_404(session, models.Lender, "id", lender_id)

        return models.CreditProduct.create(session, **credit_product.dict(), lender=lender)


@router.get(
    "/lenders/{lender_id}",
    tags=["lenders"],
    response_model=models.LenderWithRelations,
)
async def get_lender(lender_id: int, session: Session = Depends(get_db)):
    """
    Retrieve a lender by its ID.

    :param lender_id: The ID of the lender to retrieve.
    :return: The lender with the specified ID.
    :raise: HTTPException with status code 404 if the lender is not found.
    """
    return get_object_or_404(session, models.Lender, "id", lender_id)


@router.put(
    "/lenders/{id}",
    tags=["lenders"],
)
async def update_lender(
    id: int,
    payload: models.LenderBase,
    admin: models.User = Depends(dependencies.get_admin_user),
    session: Session = Depends(get_db),
) -> models.Lender:
    """
    Update an existing lender.

    :param id: The ID of the lender to update.
    :param payload: The data to update the lender with.
    :return: The updated lender.
    :raise: lumache.OCPOnlyError if the current user is not authorized.
    """
    with transaction_session(session):
        try:
            lender = get_object_or_404(session, models.Lender, "id", id)

            update_dict = jsonable_encoder(payload, exclude_unset=True)
            return lender.update(session, **update_dict)
        except IntegrityError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Lender already exists",
            )


@router.get(
    "/lenders",
    tags=["lenders"],
)
async def get_lenders_list(
    session: Session = Depends(get_db),
) -> serializers.LenderListResponse:
    """
    Get the list of all lenders.

    :return: The list of all lenders.
    """
    lenders_query = session.query(models.Lender)

    total_count = lenders_query.count()

    lenders = lenders_query.all()

    return serializers.LenderListResponse(
        items=lenders,
        count=total_count,
        page=0,
        page_size=total_count,
    )


@router.get(
    "/credit-products/{credit_product_id}",
    tags=["lenders"],
    response_model=models.CreditProductWithLender,
)
async def get_credit_product(
    credit_product_id: int,
    session: Session = Depends(get_db),
):
    """
    Retrieve a credit product by its ID, including its associated lender information.

    :param credit_product_id: The ID of the credit product to retrieve.
    :return: The credit product with the specified ID and its associated lender information.
    :raise: HTTPException with status code 404 if the credit product is not found.
    """
    creditProduct = (
        models.CreditProduct.filter_by(session, "id", credit_product_id)
        .join(models.Lender)
        .options(joinedload(models.CreditProduct.lender))
        .first()
    )
    if not creditProduct:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credit product not found")

    return creditProduct


@router.put(
    "/credit-products/{credit_product_id}",
    tags=["lenders"],
)
async def update_credit_products(
    credit_product: models.CreditProduct,
    credit_product_id: int,
    admin: models.User = Depends(dependencies.get_admin_user),
    session: Session = Depends(get_db),
) -> models.CreditProduct:
    """
    Update an existing credit product.

    :param credit_product: The credit product data to update.
    :param credit_product_id: The ID of the credit product to update.
    :return: The updated credit product.
    :raise: lumache.OCPOnlyError if the current user is not authorized.
    """
    # Rename the query parameter.
    payload = credit_product

    with transaction_session(session):
        credit_product = get_object_or_404(session, models.CreditProduct, "id", credit_product_id)

        update_dict = jsonable_encoder(payload, exclude_unset=True)
        return credit_product.update(session, **update_dict)
