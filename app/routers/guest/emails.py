import re

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app import dependencies, models, parsers, util
from app.aws import CognitoClient
from app.db import get_db, transaction_session

router = APIRouter()

valid_email = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"


@router.post(
    "/applications/change-email",
    tags=["applications"],
    response_model=parsers.ChangeEmail,
)
async def change_email(
    payload: parsers.ChangeEmail,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(dependencies.get_cognito_client),
    application: models.Application = Depends(dependencies.get_publication_as_guest_via_payload),
):
    """
    Change the email address for an application.

    :param payload: The data for changing the email address.
    :type payload: parsers.ChangeEmail

    :param session: The database session.
    :type session: Session

    :param client: The Cognito client.
    :type client: CognitoClient

    :return: The data for changing the email address.
    :rtype: parsers.ChangeEmail

    """
    with transaction_session(session):
        old_email = application.primary_email

        # Update the primary email of an application.
        email = payload.new_email
        if not re.match(valid_email, email):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="New email is not valid",
            )
        confirmation_email_token = util.generate_uuid(email)
        application.confirmation_email_token = f"{email}---{confirmation_email_token}"
        application.pending_email_confirmation = True

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.MSME_CHANGE_EMAIL,
            data=jsonable_encoder(payload, exclude_unset=True),
            application_id=application.id,
        )

        external_message_id = client.send_new_email_confirmation_to_sme(
            application.borrower.legal_name,
            payload.new_email,
            old_email,
            confirmation_email_token,
            application.uuid,
        )

        models.Message.create(
            session,
            application=application,
            type=models.MessageType.EMAIL_CHANGE_CONFIRMATION,
            external_message_id=external_message_id,
        )

        return payload


@router.post(
    "/applications/confirm-change-email",
    tags=["applications"],
    response_model=parsers.ChangeEmail,
)
async def confirm_email(
    payload: parsers.ConfirmNewEmail,
    session: Session = Depends(get_db),
    application: models.Application = Depends(dependencies.get_publication_as_guest_via_payload),
):
    """
    Confirm the email address change for an application.

    :param payload: The data for confirming the email address change.
    :type payload: parsers.ConfirmNewEmail

    :param session: The database session.
    :type session: Session

    :return: The data for confirming the email address change.
    :rtype: parsers.ChangeEmail

    """
    with transaction_session(session):
        if not application.pending_email_confirmation:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Application is not pending an email confirmation",
            )

        new_email, token = application.confirmation_email_token.split("---")[:2]
        if token != payload.confirmation_email_token:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Not authorized to modify this application",
            )

        application.primary_email = new_email
        application.pending_email_confirmation = False
        application.confirmation_email_token = ""

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.MSME_CONFIRM_EMAIL,
            data=jsonable_encoder(payload, exclude_unset=True),
            application_id=application.id,
        )

        return parsers.ChangeEmail(new_email=application.primary_email, uuid=application.uuid)
