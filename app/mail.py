import json
import logging
from pathlib import Path
from typing import Any
from urllib.parse import quote

from mypy_boto3_ses.client import SESClient
from sqlalchemy.orm import Session

from app.i18n import _
from app.models import Application, Lender, Message, MessageType
from app.settings import app_settings

logger = logging.getLogger(__name__)

BASE_TEMPLATES_PATH = Path(__file__).absolute().parent.parent / "email_templates"


def send(
    session: Session,
    ses: SESClient,
    message_type: str,
    application: Application,
    *,
    save: bool = True,
    save_kwargs: dict[str, Any] | None = None,
    **send_kwargs: Any,
) -> None:
    # `template_name` can be overridden by the match statement, if it is conditional on `send_kwargs`.
    # If so, use new template names for each condition.
    template_name = message_type.lower()

    base_application_url = f"{app_settings.frontend_url}/application/{quote(application.uuid)}"

    # `recipients` is a list of lists. Each sublist is a `ToAddresses` parameter for an email message.
    #
    # All URLs using `app_settings.frontend_url` are React routes in credere-frontend.
    match message_type:
        case MessageType.BORROWER_INVITATION | MessageType.BORROWER_PENDING_APPLICATION_REMINDER:
            recipients = [[application.primary_email]]
            subject = _("Opportunity to access MSME credit for being awarded a public contract")

            base_fathom_url = "?utm_source=credere-intro&utm_medium=email&utm_campaign="
            parameters = {
                "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
                "TENDER_TITLE": application.award.title,
                "BUYER_NAME": application.award.buyer_name,
                "FIND_OUT_MORE_URL": f"{base_application_url}/intro{base_fathom_url}intro",
                "REMOVE_ME_URL": f"{base_application_url}/decline{base_fathom_url}decline",
            }

        case MessageType.BORROWER_PENDING_SUBMIT_REMINDER:
            recipients = [[application.primary_email]]
            subject = _("Reminder - Opportunity to access MSME credit for being awarded a public contract")
            parameters = {
                "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
                "TENDER_TITLE": application.award.title,
                "BUYER_NAME": application.award.buyer_name,
                "APPLY_FOR_CREDIT_URL": f"{base_application_url}/intro",
                "REMOVE_ME_URL": f"{base_application_url}/decline",
            }

        case MessageType.SUBMISSION_COMPLETED:
            recipients = [[application.primary_email]]
            subject = _("Application Submission Complete")
            parameters = {
                "LENDER_NAME": application.lender.name,
                "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
            }

        case MessageType.NEW_APPLICATION_OCP:
            recipients = [[app_settings.ocp_email_group]]
            subject = _("New application submission")
            parameters = {"LOGIN_URL": f"{app_settings.frontend_url}/login", "LENDER_NAME": application.lender.name}

        case MessageType.NEW_APPLICATION_FI:
            recipients = [_get_lender_emails(application.lender, MessageType.NEW_APPLICATION_FI)]
            subject = _("New application submission")
            parameters = {"LOGIN_URL": f"{app_settings.frontend_url}/login"}

        case MessageType.FI_MESSAGE:
            recipients = [[application.primary_email]]
            subject = _("New message from a financial institution")
            parameters = {
                "LENDER_NAME": application.lender.name,
                "LENDER_MESSAGE": send_kwargs["message"],
                "LOGIN_DOCUMENTS_URL": f"{base_application_url}/documents",
            }

        case MessageType.BORROWER_DOCUMENT_UPDATED:
            recipients = [_get_lender_emails(application.lender, MessageType.BORROWER_DOCUMENT_UPDATED)]
            subject = _("Application updated")
            parameters = {"LOGIN_URL": f"{app_settings.frontend_url}/login"}

        case MessageType.REJECTED_APPLICATION:
            recipients = [[application.primary_email]]
            subject = _("Your credit application has been declined")
            parameters = {
                "LENDER_NAME": application.lender.name,
                "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
            }

            if send_kwargs["options"]:
                template_name = "rejected_application_alternatives"
                parameters["FIND_ALTENATIVE_URL"] = f"{base_application_url}/find-alternative-credit"
            else:
                template_name = "rejected_application_no_alternatives"

        case MessageType.APPROVED_APPLICATION:
            if application.lender.default_pre_approval_message:
                additional_comments = application.lender.default_pre_approval_message
            elif application.lender_approved_data.get("additional_comments"):
                additional_comments = application.lender_approved_data["additional_comments"]
            else:
                additional_comments = "Ninguno"

            recipients = [[application.primary_email]]
            subject = _("Your credit application has been prequalified")
            parameters = {
                "LENDER_NAME": application.lender.name,
                "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
                "TENDER_TITLE": application.award.title,
                "BUYER_NAME": application.award.buyer_name,
                "ADDITIONAL_COMMENTS": additional_comments,
                "UPLOAD_CONTRACT_URL": f"{base_application_url}/upload-contract",
            }

        case MessageType.CONTRACT_UPLOAD_CONFIRMATION:
            recipients = [[application.primary_email]]
            subject = _("Thank you for uploading the signed contract")
            parameters = {
                "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
                "TENDER_TITLE": application.award.title,
                "BUYER_NAME": application.award.buyer_name,
            }

        case MessageType.CONTRACT_UPLOAD_CONFIRMATION_TO_FI:
            recipients = [_get_lender_emails(application.lender, MessageType.CONTRACT_UPLOAD_CONFIRMATION_TO_FI)]
            subject = _("New contract submission")
            parameters = {"LOGIN_URL": f"{app_settings.frontend_url}/login"}

        case MessageType.CREDIT_DISBURSED:
            recipients = [[application.primary_email]]
            subject = _("Your credit application has been approved")
            parameters = {
                "LENDER_NAME": application.lender.name,
                "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
                "LENDER_EMAIL": application.lender.email_group,
            }

        case MessageType.OVERDUE_APPLICATION:
            recipients = [[app_settings.ocp_email_group]]
            subject = _("New overdue application")
            parameters = {
                "USER": application.lender.name,
                "LENDER_NAME": application.lender.name,
                "LOGIN_URL": f"{app_settings.frontend_url}/login",
            }

        case MessageType.APPLICATION_COPIED:
            recipients = [[application.primary_email]]
            subject = _("Alternative credit option")
            parameters = {
                "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
                "CONTINUE_URL": f"{app_settings.frontend_url}/application/{application.uuid}/credit-options",
            }

        case MessageType.EMAIL_CHANGE_CONFIRMATION:
            recipients = [
                [application.primary_email],
                [send_kwargs["new_email"]],
            ]
            subject = _("Confirm email address change")
            parameters = {
                "NEW_MAIL": send_kwargs["new_email"],
                "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
                "CONFIRM_EMAIL_CHANGE_URL": (
                    f"{base_application_url}/change-primary-email"
                    f"?token={quote(send_kwargs['confirmation_email_token'])}"
                ),
            }

        case _:
            raise NotImplementedError

    # If at least one email address is the borrower's, assume all are the borrower's.
    to_borrower = [application.primary_email] in recipients

    # Only the last message ID is saved, if multiple email messages are sent.
    for to_addresses in recipients:
        message_id = _send_email(
            ses,
            to_addresses=to_addresses,
            to_borrower=to_borrower,
            subject=subject,
            template_name=template_name,
            parameters=parameters,
        )

    if save:
        if save_kwargs is None:
            save_kwargs = {}
        Message.create(
            session, application=application, type=message_type, external_message_id=message_id, **save_kwargs
        )


def _send_email(
    ses: SESClient,
    *,
    to_addresses: list[str],
    to_borrower: bool = True,
    subject: str,
    template_name: str,
    parameters: dict[str, str],
) -> str:
    original_addresses = to_addresses.copy()

    if app_settings.environment != "production" and to_borrower:
        to_addresses = [app_settings.test_mail_receiver]

    if not to_addresses:
        logger.error("No email address provided!")  # ideally, it should be impossible for a lender to have no users
        return ""

    # Read the HTML template and replace its parameters (like ``BUYER_NAME``).
    parameters.setdefault("IMAGES_BASE_URL", app_settings.images_base_url)
    content = (BASE_TEMPLATES_PATH / f"{template_name}.{app_settings.email_template_lang}.html").read_text()
    for key, value in parameters.items():
        content = content.replace("{{%s}}" % key, value)

    logger.info("%s - Email to: %s sent to %s", app_settings.environment, original_addresses, to_addresses)
    return ses.send_templated_email(
        Source=app_settings.email_sender_address,
        Destination={"ToAddresses": to_addresses},
        ReplyToAddresses=[app_settings.ocp_email_group],
        Template=f"credere-main-{app_settings.email_template_lang}",
        TemplateData=json.dumps(
            {
                "SUBJECT": f"Credere - {subject}",
                "CONTENT": content,
                "FRONTEND_URL": app_settings.frontend_url,
                "IMAGES_BASE_URL": app_settings.images_base_url,
            }
        ),
    )["MessageId"]


def _get_lender_emails(lender: Lender, message_type: MessageType) -> list[str]:
    return [user.email for user in lender.users if user.notification_preferences.get(message_type)]


def send_new_user(ses: SESClient, *, name: str, username: str, temporary_password: str) -> str:
    """
    Sends an email to a new user with a link to set their password.

    This function generates an email message for new users, providing them with
    a temporary password and a link to set their password. The email is sent to the
    username (which is an email address) provided.

    :param name: The name of the new user.
    :param username: The username (email address) of the new user.
    :param temporary_password: The temporary password for the new user.
    """
    return _send_email(
        ses,
        to_addresses=[username],
        to_borrower=False,
        subject=_("Welcome"),
        template_name="new_user",
        parameters={
            "USER": name,
            "LOGIN_URL": (
                f"{app_settings.frontend_url}/create-password"
                f"?key={quote(temporary_password)}&email={quote(username)}"
            ),
        },
    )


def send_reset_password(ses: SESClient, *, username: str, temporary_password: str) -> str:
    """
    Sends an email to a user with instructions to reset their password.

    This function generates and sends an email message to a user providing a link
    for them to reset their password.

    :param username: The username associated with the account for which the password is to be reset.
    :param temporary_password: A temporary password generated for the account.
    """
    return _send_email(
        ses,
        to_addresses=[username],
        to_borrower=False,
        subject=_("Reset password"),
        template_name="reset_password",
        parameters={
            "USER_ACCOUNT": username,
            "RESET_PASSWORD_URL": (
                f"{app_settings.frontend_url}/create-password"
                f"?key={quote(temporary_password)}&email={quote(username)}"
            ),
        },
    )


def send_overdue_application_to_lender(ses: SESClient, *, lender: Lender, amount: int) -> str:
    """
    Sends an email notification to the lender about overdue applications.

    :param lender: The overdue lender.
    :param amount: Number of overdue applications.
    """
    return _send_email(
        ses,
        to_addresses=_get_lender_emails(lender, MessageType.OVERDUE_APPLICATION),
        to_borrower=False,
        subject=_("You have credit applications that need processing"),
        template_name="overdue_application_to_lender",
        parameters={
            "USER": lender.name,
            "NUMBER_APPLICATIONS": str(amount),
            "LOGIN_URL": f"{app_settings.frontend_url}/login",
        },
    )
