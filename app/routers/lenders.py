from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app import dependencies, models, serializers, util
from app.db import get_db, rollback_on_error
from app.i18n import _
from app.sources import colombia as data_access
from app.util import get_object_or_404

router = APIRouter()


@router.post(
    "/lenders",
    tags=[util.Tags.lenders],
)
async def create_lender(
    payload: models.LenderCreate,
    admin: Annotated[models.User, Depends(dependencies.get_admin_user)],
    session: Annotated[Session, Depends(get_db)],
) -> models.Lender:
    """
    Create a new lender.

    :param payload: The lender data to be created.
    :return: The created lender.
    :raise: lumache.OCPOnlyError if the current user is not authorized.
    """
    with rollback_on_error(session):
        try:
            # Create a Lender instance without the credit_product data
            lender = models.Lender(**payload.model_dump(exclude={"credit_products"}))
            session.add(lender)

            # Create a CreditProduct instance for each credit product and add it to the lender
            if payload.credit_products:
                for credit_product in payload.credit_products:
                    session.add(models.CreditProduct(**credit_product.model_dump(), lender=lender))

            session.commit()
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_("Lender with that name already exists"),
            ) from None
        return lender


@router.post(
    "/lenders/{lender_id}/credit-products",
    tags=[util.Tags.lenders],
)
async def create_credit_products(
    lender_id: int,
    payload: models.CreditProduct,
    admin: Annotated[models.User, Depends(dependencies.get_admin_user)],
    session: Annotated[Session, Depends(get_db)],
) -> models.CreditProduct:
    """
    Create a new credit product for a specific lender.

    :param payload: The credit product data to be created.
    :param lender_id: The ID of the lender for which the credit product will be created.
    :return: The created credit product.
    :raise: lumache.OCPOnlyError if the current user is not authorized.
    """
    with rollback_on_error(session):
        lender = get_object_or_404(session, models.Lender, "id", lender_id)
        credit_product = models.CreditProduct.create(session, **payload.model_dump(), lender=lender)

        session.commit()
        return credit_product


@router.get(
    "/lenders/{lender_id}",
    tags=[util.Tags.lenders],
    response_model=models.LenderWithRelations,
)
async def get_lender(
    lender_id: int,
    session: Annotated[Session, Depends(get_db)],
) -> Any:
    """
    Retrieve a lender by its ID.

    :param lender_id: The ID of the lender to retrieve.
    :return: The lender with the specified ID.
    :raise: HTTPException if the lender is not found.
    """
    return get_object_or_404(session, models.Lender, "id", lender_id)


@router.put(
    "/lenders/{lender_id}",
    tags=[util.Tags.lenders],
)
async def update_lender(
    lender_id: int,
    payload: models.LenderBase,
    admin: Annotated[models.User, Depends(dependencies.get_admin_user)],
    session: Annotated[Session, Depends(get_db)],
) -> models.Lender:
    """
    Update an existing lender.

    :param lender_id: The ID of the lender to update.
    :param payload: The data to update the lender with.
    :return: The updated lender.
    :raise: lumache.OCPOnlyError if the current user is not authorized.
    """
    with rollback_on_error(session):
        try:
            lender = get_object_or_404(session, models.Lender, "id", lender_id)
            lender = lender.update(session, **jsonable_encoder(payload, exclude_unset=True))

            session.commit()
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_("Lender with that name already exists"),
            ) from None
        return lender


@router.get(
    "/lenders",
    tags=[util.Tags.lenders],
)
async def get_lenders_list(
    session: Annotated[Session, Depends(get_db)],
) -> serializers.LenderListResponse:
    """
    Get the list of all lenders.

    :return: The list of all lenders.
    """
    lenders = session.query(models.Lender).all()
    total_count = len(lenders)

    return serializers.LenderListResponse(
        items=lenders,
        count=total_count,
        page=0,
        page_size=total_count,
    )


@router.get(
    "/procurement-categories",
    tags=[util.Tags.lenders],
)
async def get_procurement_categories_from_source() -> list[str]:
    """
    Get the list of the existing procurement categories from the source.

    :return: The list of existing procurement categories.
    """
    return data_access.PROCUREMENT_CATEGORIES


@router.get(
    "/credit-products/{credit_product_id}",
    tags=[util.Tags.lenders],
    response_model=models.CreditProductWithLender,
)
async def get_credit_product(
    credit_product_id: int,
    session: Annotated[Session, Depends(get_db)],
) -> Any:
    """
    Retrieve a credit product by its ID, including its associated lender information.

    :param credit_product_id: The ID of the credit product to retrieve.
    :return: The credit product with the specified ID and its associated lender information.
    :raise: HTTPException if the credit product is not found.
    """
    credit_product = (
        models.CreditProduct.filter_by(session, "id", credit_product_id)
        .join(models.Lender)
        .options(joinedload(models.CreditProduct.lender))
        .first()
    )
    if not credit_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_("Credit product not found"),
        ) from None

    return credit_product


@router.put(
    "/credit-products/{credit_product_id}",
    tags=[util.Tags.lenders],
)
async def update_credit_products(
    credit_product_id: int,
    payload: models.CreditProduct,
    admin: Annotated[models.User, Depends(dependencies.get_admin_user)],
    session: Annotated[Session, Depends(get_db)],
) -> models.CreditProduct:
    """
    Update an existing credit product.

    :param payload: The credit product data to update.
    :param credit_product_id: The ID of the credit product to update.
    :return: The updated credit product.
    :raise: lumache.OCPOnlyError if the current user is not authorized.
    """
    with rollback_on_error(session):
        credit_product = get_object_or_404(session, models.CreditProduct, "id", credit_product_id)
        credit_product = credit_product.update(session, **jsonable_encoder(payload, exclude_unset=True))

        session.commit()
        return credit_product
