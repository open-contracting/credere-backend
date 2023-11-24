from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

import app.utils.applications as utils
from app import models, parsers
from app.aws import CognitoClient, get_cognito_client
from app.db import get_db, transaction_session

router = APIRouter()


@router.post(
    "/applications/change-email",
    tags=["applications"],
    response_model=parsers.ChangeEmail,
)
async def change_email(
    payload: parsers.ChangeEmail,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(get_cognito_client),
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
        application = utils.get_application_by_uuid(payload.uuid, session)
        old_email = application.primary_email
        confirmation_email_token = utils.update_application_primary_email(application, payload.new_email)
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
        application = utils.get_application_by_uuid(payload.uuid, session)

        utils.check_pending_email_confirmation(application, payload.confirmation_email_token)

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.MSME_CONFIRM_EMAIL,
            data=jsonable_encoder(payload, exclude_unset=True),
            application_id=application.id,
        )

        return parsers.ChangeEmail(new_email=application.primary_email, uuid=application.uuid)
