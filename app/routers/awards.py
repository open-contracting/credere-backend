from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..schema.core_tables.core import Award

router = APIRouter()


@router.get("/awards/{award_id}", tags=["awards"], response_model=Award)
async def get_award(award_id: int, db: Session = Depends(get_db)):
    print(award_id)
    user = db.query(Award).filter(Award.id == award_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/awards/", tags=["awards"], response_model=Award)
async def create_award(award: Award, db: Session = Depends(get_db)):
    award.created_at = datetime.now()
    award.updated_at = datetime.now()
    award.contractperiod_startdate = datetime.now()
    award.contractperiod_enddate = datetime.now()
    db_award = Award(**award.dict())
    db.add(db_award)
    db.commit()
    db.refresh(db_award)

    return award
