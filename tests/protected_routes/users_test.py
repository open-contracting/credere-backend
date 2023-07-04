import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.user_dependencies import CognitoClient, get_cognito_client
from app.db.session import get_db, transaction_session
from app.schema.core import User

router = APIRouter()


@router.post("/users-test", tags=["users"], response_model=User)
async def create_user(
    payload: User,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(get_cognito_client),
):
    with transaction_session(session):
        try:
            user = User(**payload.dict())

            session.add(user)
            cognitoResponse = client.admin_create_user(payload.email, payload.name)
            user.external_id = cognitoResponse["User"]["Username"]

            return user
        except (client.exceptions().UsernameExistsException, IntegrityError) as e:
            logging.error(e)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Username already exists",
            )
