from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import app.utils.lenders as utils
from app.schema import api as ApiSchema

from ..db.session import get_db, transaction_session
from ..schema import core
from ..utils.permissions import OCP_only
from ..utils.verify_token import get_current_user, get_user

router = APIRouter()


@router.post(
    "/lenders/",
    tags=["lenders"],
    response_model=core.Lender,
)
@OCP_only()
async def create_lender(
    lender: core.Lender,
    current_user: core.User = Depends(get_current_user),
    session: Session = Depends(get_db),
    user: core.User = None,
):
    with transaction_session(session):
        return utils.create_lender(session, lender, user)


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
    user: core.User = None,
):
    with transaction_session(session):
        return utils.update_lender(session, lender, id)


@router.get(
    "/lenders/",
    tags=["lenders"],
    response_model=ApiSchema.LenderPagination,
)
@OCP_only()
async def get_lenders_list(
    page: int = Query(1, gt=0),
    page_size: int = Query(10, gt=0),
    current_user: core.User = Depends(get_current_user),
    session: Session = Depends(get_db),
    user: core.User = None,
):
    return utils.get_all_lenders(page, page_size, session)
