from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..schema.user_tables.users import User

router = APIRouter()


@router.get("/users/{user_id}", tags=["users"], response_model=User)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    print(user_id)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/users/", tags=["users"], response_model=User)
async def create_user(user: User, db: Session = Depends(get_db)):
    user.created_at = datetime.now()
    db_user = User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return user
