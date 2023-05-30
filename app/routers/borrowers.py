from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..schema.core_tables.core import Borrower

router = APIRouter()


@router.get("/borrowers/{borrower_id}", tags=["borrowers"], response_model=Borrower)
async def get_award(borrower_id: int, db: Session = Depends(get_db)):
    user = db.query(Borrower).filter(Borrower.id == borrower_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/borrowers/")  # , tags=["borrowers"], response_model=Borrower)
async def create_award(borrower: Borrower, db: Session = Depends(get_db)):
    obj_db = Borrower(**borrower.dict())
    db.add(obj_db)
    db.commit()
    db.refresh(obj_db)

    return obj_db
