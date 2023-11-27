from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Borrower
from app.util import get_object_or_404

router = APIRouter()


@router.get("/borrowers/{borrower_id}", tags=["borrowers"], response_model=Borrower)
async def get_borrowers(borrower_id: int, session: Session = Depends(get_db)):
    """
    Retrieve a borrower by ID.

    :param borrower_id: The ID of the borrower to retrieve.
    :return: The retrieved borrower.
    """
    return get_object_or_404(session, Borrower, "id", borrower_id)


@router.post("/borrowers/", tags=["borrowers"], response_model=Borrower)
async def create_borrowers(borrower: Borrower, session: Session = Depends(get_db)):
    """
    Create a new borrower.

    :param borrower: The borrower data to create.
    :return: The created borrower.
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
    response_model=list[str],
)
async def get_borrowers_contracting_process_ids(session: Session = Depends(get_db)):
    """
    Get the list of borrower identifiers in descending order of creation.

    :return: The list of borrower identifiers.
    """
    borrowers = session.query(Borrower.borrower_identifier).order_by(desc(Borrower.created_at)).all()
    if not borrowers:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No borrowers found")
    return [borrower[0] for borrower in borrowers]
