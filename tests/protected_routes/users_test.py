from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import aws, dependencies, models
from app.db import get_db

router = APIRouter()


@router.post("/create-test-user-headers", tags=["users"])
async def create_test_user_headers(
    payload: models.User,
    session: Session = Depends(get_db),
    client: aws.CognitoClient = Depends(dependencies.get_cognito_client),
):
    # Like create_user().
    user = models.User.create(session, **payload.model_dump())
    response = client.admin_create_user(payload.email, payload.name)
    user.external_id = response["User"]["Username"]
    session.commit()

    # Like change_password().
    response = client.initiate_auth(payload.email, "initial-autogenerated-password")
    if response["ChallengeName"] == "NEW_PASSWORD_REQUIRED":
        session = response["Session"]
        response = client.respond_to_auth_challenge(
            username=payload.email,
            session=session,
            challenge_name="NEW_PASSWORD_REQUIRED",
            new_password="12345-UPPER-lower",
        )
    client.verified_email(payload.email)

    return {"Authorization": "Bearer " + response["AuthenticationResult"]["AccessToken"]}
