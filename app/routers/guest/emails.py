from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app import aws, dependencies, mail, models, parsers, util
from app.db import get_db, rollback_on_error
from app.i18n import _

router = APIRouter()


@router.post(
    "/applications/change-email",
    tags=[util.Tags.applications],
)
async def change_email(
    payload: parsers.ChangeEmail,
    session: Session = Depends(get_db),
    client: aws.Client = Depends(dependencies.get_aws_client),
    application: models.Application = Depends(dependencies.get_application_as_guest_via_payload),
) -> parsers.ChangeEmail:
    """
    Change the email address for an application.

    :param payload: The data for changing the email address.
    :return: The data for changing the email address.
    """
    with rollback_on_error(session):
        # Update the primary email of an application.
        new_email = payload.new_email
        if not util.is_valid_email(new_email):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=_("New email is not valid"),
            )

        confirmation_email_token = util.generate_uuid(new_email)
        application.confirmation_email_token = f"{new_email}---{confirmation_email_token}"
        application.pending_email_confirmation = True

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.MSME_CHANGE_EMAIL,
            data=jsonable_encoder(payload, exclude_unset=True),
            application_id=application.id,
        )

        mail.send(
            session,
            client.ses,
            models.MessageType.EMAIL_CHANGE_CONFIRMATION,
            application,
            new_email=payload.new_email,
            confirmation_email_token=confirmation_email_token,
        )

        session.commit()
        return payload


@router.post(
    "/applications/confirm-change-email",
    tags=[util.Tags.applications],
)
async def confirm_email(
    payload: parsers.ConfirmNewEmail,
    session: Session = Depends(get_db),
    application: models.Application = Depends(dependencies.get_application_as_guest_via_payload),
) -> parsers.ChangeEmail:
    """
    Confirm the email address change for an application.

    :param payload: The data for confirming the email address change.
    :return: The data for confirming the email address change.
    """
    with rollback_on_error(session):
        if not application.pending_email_confirmation:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=_("Application is not pending an email confirmation"),
            )

        new_email, token = application.confirmation_email_token.split("---")[:2]
        if token != payload.confirmation_email_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_("Not authorized to modify this application"),
            )

        # The email address for the Borrower instance is not updated, because, between invitations, the borrower might
        # have updated their email address in the data source. Borrowers typically change the email address to direct
        # messages to the responsible person (who might be different from the general contact in the data source).
        application.primary_email = new_email
        application.pending_email_confirmation = False
        application.confirmation_email_token = ""

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.MSME_CONFIRM_EMAIL,
            data=jsonable_encoder(payload, exclude_unset=True),
            application_id=application.id,
        )

        session.commit()
        return parsers.ChangeEmail(new_email=application.primary_email, uuid=application.uuid)
