from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..schema.core_tables.core import Award

router = APIRouter()


@router.get("/awards/{award_id}", tags=["awards"], response_model=Award)
async def get_award(award_id: int, db: Session = Depends(get_db)):
    award = db.query(Award).filter(Award.id == award_id).first()
    if not award:
        raise HTTPException(status_code=404, detail="Award not found")
    return award


@router.get("/awards/last/", tags=["awards"], response_model=Award)
async def get_last_award(db: Session = Depends(get_db)):
    award = db.query(Award).order_by(desc(Award.created_at)).first()
    if not award:
        raise HTTPException(status_code=404, detail="Award not found")
    return award


@router.post("/awards/", tags=["awards"], response_model=Award)
async def create_award(award: Award, db: Session = Depends(get_db)):
    award.contractperiod_startdate = datetime.now()
    award.contractperiod_enddate = datetime.now()
    db_award = Award(**award.dict())
    db.add(db_award)
    db.commit()
    db.refresh(db_award)

    return award
