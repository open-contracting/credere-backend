from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

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
    lender: core.LenderBase,
    current_user: core.User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    with transaction_session(session):
        return utils.create_lender(session, lender)


@router.get("/lenders/{lender_id}", tags=["lenders"], response_model=core.Lender)
async def get_lender(lender_id: int, db: Session = Depends(get_db)):
    lender = db.query(core.Lender).filter(core.Lender.id == lender_id).first()

    if not lender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lender not found"
        )
    return lender


@router.put(
    "/lenders/{id}",
    tags=["lenders"],
    response_model=core.Lender,
)
@OCP_only()
async def update_lender(
    id: int,
    lender: core.Lender,
    current_user: core.User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    with transaction_session(session):
        return utils.update_lender(session, lender, id)


@router.get(
    "/lenders",
    tags=["lenders"],
    response_model=ApiSchema.LenderListResponse,
)
async def get_lenders_list(
    session: Session = Depends(get_db),
):
    return utils.get_all_lenders(session)
