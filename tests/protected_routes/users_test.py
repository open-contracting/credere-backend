from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import dependencies
from app.aws import CognitoClient
from app.db import get_db
from app.models import User

temp_password = "1234567890Abc!!"
new_password = "!!!1234567890Abc!!"

router = APIRouter()


@router.post("/create-test-user-headers", tags=["users"])
async def create_test_user_headers(
    payload: User,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(dependencies.get_cognito_client),
):
    user = User(**payload.model_dump())

    cognito_response = client.admin_create_user(payload.email, payload.name)
    user.external_id = cognito_response["User"]["Username"]

    session.add(user)
    session.commit()

    client.verified_email(payload.email)
    response = client.initiate_auth(payload.email, temp_password)
    if response["ChallengeName"] == "NEW_PASSWORD_REQUIRED":
        session = response["Session"]
        response = client.respond_to_auth_challenge(payload.email, session, "NEW_PASSWORD_REQUIRED", new_password)

    return {"Authorization": "Bearer " + response["AuthenticationResult"]["AccessToken"]}
