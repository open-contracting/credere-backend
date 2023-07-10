from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import app.utils.users as utils
from app.core.user_dependencies import CognitoClient, get_cognito_client
from app.db.session import get_db
from app.schema.core import User

router = APIRouter()


@router.post("/users-test", tags=["users"], response_model=User)
async def create_test_user(
    payload: User,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(get_cognito_client),
):
    return utils.create_user(payload, session, client)
