from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Borrower

router = APIRouter()


@router.post("/borrowers-test", tags=["borrowers"], response_model=Borrower)
async def create_test_borrower(
    payload: Borrower,
    session: Session = Depends(get_db),
):
    session.add(payload)
    session.commit()
    session.refresh(payload)

    return payload
