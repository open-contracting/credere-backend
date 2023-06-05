from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..schema.core import Award

router = APIRouter()


@router.get("/awards/{award_id}", tags=["awards"], response_model=Award)
async def get_award(award_id: int, session: Session = Depends(get_db)):
    award = session.query(Award).filter(Award.id == award_id).first()
    if not award:
        raise HTTPException(status_code=404, detail="Award not found")
    return award


@router.get("/awards/get-last-award/", tags=["awards"], response_model=Award)
async def get_last_award(session: Session = Depends(get_db)):
    award = session.query(Award).order_by(desc(Award.created_at)).first()
    if not award:
        raise HTTPException(status_code=404, detail="Award not found")
    return award


@router.post("/awards/", tags=["awards"], response_model=Award)
async def create_award(award: Award, session: Session = Depends(get_db)):
    db_award = Award(**award.dict())
    session.add(db_award)
    session.commit()
    session.refresh(db_award)

    return award
