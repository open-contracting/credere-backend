from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..schema.core import Borrower

router = APIRouter()


@router.get("/borrowers/{borrower_id}", tags=["borrowers"], response_model=Borrower)
async def get_borrowers(borrower_id: int, session: Session = Depends(get_db)):
    """
    Retrieve a borrower by ID.

    :param borrower_id: The ID of the borrower to retrieve.
    :type borrower_id: int
    :param session: The database session.
    :type session: Session

    :return: The retrieved borrower.
    :rtype: Borrower
    """
    borrower = Borrower.first_by(session, "id", borrower_id)
    if not borrower:
        raise HTTPException(status_code=404, detail="Borrower not found")
    return borrower


@router.post("/borrowers/", tags=["borrowers"], response_model=Borrower)
async def create_borrowers(borrower: Borrower, session: Session = Depends(get_db)):
    """
    Create a new borrower.

    :param borrower: The borrower data to create.
    :type borrower: Borrower
    :param session: The database session.
    :type session: Session

    :return: The created borrower.
    :rtype: Borrower
    """
    borrower.created_at = datetime.now()
    borrower.updated_at = datetime.now()
    borrower.declined_at = datetime.now()
    obj_db = Borrower(**borrower.dict())
    session.add(obj_db)
    session.commit()
    session.refresh(obj_db)

    return obj_db


@router.get(
    "/borrowers/get-borrower-identifiers/",
    tags=["awards"],
    response_model=List[str],
)
async def get_borrowers_contracting_process_ids(session: Session = Depends(get_db)):
    """
    Get the list of borrower identifiers in descending order of creation.

    :param session: The database session.
    :type session: Session

    :return: The list of borrower identifiers.
    :rtype: List[str]
    """
    borrowers = session.query(Borrower.borrower_identifier).order_by(desc(Borrower.created_at)).all()
    if not borrowers:
        raise HTTPException(status_code=404, detail="No borrowers found")
    return [borrower[0] for borrower in borrowers]
