from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Award
from app.util import get_object_or_404

router = APIRouter()


@router.get("/awards/{award_id}", tags=["awards"], response_model=Award)
async def get_award(award_id: int, session: Session = Depends(get_db)):
    """
    Retrieve an award by its ID.

    :param award_id: The ID of the award to retrieve.
    :type award_id: int

    :param session: The database session.
    :type session: Session

    :return: The award with the specified ID.
    :rtype: Award

    :raise: HTTPException with status code 404 if the award is not found."""
    return get_object_or_404(session, Award, "id", award_id)


@router.get("/awards/get-last-award/", tags=["awards"], response_model=Award)
async def get_last_award(session: Session = Depends(get_db)):
    """
    Retrieve the last (most recent) award.

    :param session: The database session.
    :type session: Session

    :return: The last award.
    :rtype: Award

    :raise: HTTPException with status code 404 if no awards are found.
    """
    award = session.query(Award).order_by(desc(Award.created_at)).first()
    if not award:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Award not found")
    return award


@router.post("/awards/", tags=["awards"], response_model=Award)
async def create_award(award: Award, session: Session = Depends(get_db)):
    """
    Create a new award.

    :param award: The award data to be created.
    :type award: Award
    :param session: The database session.
    :type session: Session

    :return: The created award.
    :rtype: Award"""
    db_award = Award(**award.dict())
    session.add(db_award)
    session.commit()
    session.refresh(db_award)

    return award
