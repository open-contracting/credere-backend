from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..schema.core import Borrower

router = APIRouter()


@router.get("/borrowers/{borrower_id}", tags=["borrowers"], response_model=Borrower)
async def get_borrowers(borrower_id: int, db: Session = Depends(get_db)):
    borrower = db.query(Borrower).filter(Borrower.id == borrower_id).first()
    if not borrower:
        raise HTTPException(status_code=404, detail="Borrower not found")
    return borrower


@router.post("/borrowers/", tags=["borrowers"], response_model=Borrower)
async def create_borrowers(borrower: Borrower, db: Session = Depends(get_db)):
    borrower.created_at = datetime.now()
    borrower.updated_at = datetime.now()
    borrower.declined_at = datetime.now()
    obj_db = Borrower(**borrower.dict())
    db.add(obj_db)
    db.commit()
    db.refresh(obj_db)

    return obj_db


@router.get(
    "/borrowers/get-borrower-identifiers/",
    tags=["awards"],
    response_model=List[str],
)
async def get_borrowers_contracting_process_ids(session: Session = Depends(get_db)):
    borrowers = (
        session.query(Borrower.borrower_identifier)
        .order_by(desc(Borrower.created_at))
        .all()
    )
    if not borrowers:
        raise HTTPException(status_code=404, detail="No borrowers found")
    return [borrower[0] for borrower in borrowers]
