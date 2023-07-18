from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import app.utils.lenders as utils
from app.core.user_dependencies import CognitoClient, get_cognito_client
from app.db.session import get_db
from app.schema.core import Lender

router = APIRouter()


@router.post("/lenders-test", tags=["lenders"], response_model=Lender)
async def create_test_user(
    payload: Lender,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(get_cognito_client),
):
    lender = utils.create_lender(session, payload)

    session.flush()
    return lender
