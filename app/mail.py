import json
import logging
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

from mypy_boto3_ses.client import SESClient

from app.i18n import _
from app.models import Application, Lender, MessageType
from app.settings import app_settings

logger = logging.getLogger(__name__)

BASE_TEMPLATES_PATH = os.path.join(Path(__file__).absolute().parent.parent, "email_templates")


def get_template_data(template_name: str, subject: str, parameters: dict[str, Any]) -> dict[str, str]:
    """
    Read the HTML file and replace its parameters (like ``BUYER_NAME``) to use as the ``{{CONTENT}}`` tag in the email
    template, then return all tags required by the email template.
    """
    with open(
        os.path.join(
            BASE_TEMPLATES_PATH, f"{template_name}{'_es' if app_settings.email_template_lang == 'es' else ''}.html"
        ),
        encoding="utf-8",
    ) as f:
        html = f.read()

    parameters.setdefault("IMAGES_BASE_URL", app_settings.images_base_url)
    for key, value in parameters.items():
        html = html.replace("{{%s}}" % key, str(value))

    return {
        "CONTENT": html,
        "SUBJECT": f"Credere - {subject}",
        "FRONTEND_URL": app_settings.frontend_url,
        "IMAGES_BASE_URL": app_settings.images_base_url,
    }


def send_email(ses: SESClient, emails: list[str], data: dict[str, str], *, to_borrower: bool = True) -> str:
    if app_settings.environment == "production" or not to_borrower:
        to_addresses = emails
    else:
        to_addresses = [app_settings.test_mail_receiver]
    if not to_addresses:
        logger.error("No email address provided!")  # ideally, it should be impossible for a lender to have no users
        return ""
    logger.info("%s - Email to: %s sent to %s", app_settings.environment, emails, to_addresses)
    return ses.send_templated_email(
        Source=app_settings.email_sender_address,
        Destination={"ToAddresses": to_addresses},
        ReplyToAddresses=[app_settings.ocp_email_group],
        Template=f"credere-main-{app_settings.email_template_lang}",
        TemplateData=json.dumps(data),
    )["MessageId"]


def get_lender_emails(lender: Lender, message_type: MessageType):
    return [user.email for user in lender.users if user.notification_preferences.get(message_type)]


def send_application_approved_email(ses: SESClient, application: Application) -> str:
    """
    Sends an email notification when an application has been approved.

    This function generates an email message with the application details and a
    link to upload the contract. The email is sent to the primary email address associated
    with the application. The function utilizes the SES (Simple Email Service) client to send the email.
    """
    parameters = {
        "LENDER_NAME": application.lender.name,
        "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
        "TENDER_TITLE": application.award.title,
        "BUYER_NAME": application.award.buyer_name,
        "UPLOAD_CONTRACT_URL": f"{app_settings.frontend_url}/application/{quote(application.uuid)}/upload-contract",
    }

    if application.lender.default_pre_approval_message:
        parameters["ADDITIONAL_COMMENTS"] = application.lender.default_pre_approval_message
    elif (
        "additional_comments" in application.lender_approved_data
        and application.lender_approved_data["additional_comments"]
    ):
        parameters["ADDITIONAL_COMMENTS"] = application.lender_approved_data["additional_comments"]
    else:
        parameters["ADDITIONAL_COMMENTS"] = "Ninguno"

    return send_email(
        ses,
        [application.primary_email],
        get_template_data("Application_approved", _("Your credit application has been prequalified"), parameters),
    )


def send_application_submission_completed(ses: SESClient, application: Application) -> str:
    """
    Sends an email notification when an application is submitted.

    The email is sent to the primary email address associated
    with the application. The function utilizes the SES (Simple Email Service) client to send the email.
    """
    return send_email(
        ses,
        [application.primary_email],
        get_template_data(
            "Application_submitted",
            _("Application Submission Complete"),
            {
                "LENDER_NAME": application.lender.name,
                "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
            },
        ),
    )


def send_application_credit_disbursed(ses: SESClient, application: Application) -> str:
    """
    Sends an email notification when an application has the credit dibursed.

    The email is sent to the primary email address associated
    with the application. The function utilizes the SES (Simple Email Service) client to send the email.
    """
    return send_email(
        ses,
        [application.primary_email],
        get_template_data(
            "Application_credit_disbursed",
            _("Your credit application has been approved"),
            {
                "LENDER_NAME": application.lender.name,
                "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
                "LENDER_EMAIL": application.lender.email_group,
            },
        ),
    )


def send_mail_to_new_user(ses: SESClient, name: str, username: str, temporary_password: str) -> str:
    """
    Sends an email to a new user with a link to set their password.

    This function generates an email message for new users, providing them with
    a temporary password and a link to set their password. The email is sent to the
    username (which is an email address) provided.

    :param name: The name of the new user.
    :param username: The username (email address) of the new user.
    :param temporary_password: The temporary password for the new user.
    """
    return send_email(
        ses,
        [username],
        get_template_data(
            "New_Account_Created",
            _("Welcome"),
            {
                "USER": name,
                "LOGIN_URL": (
                    f"{app_settings.frontend_url}/create-password"
                    f"?key={quote(temporary_password)}&email={quote(username)}"
                ),
            },
        ),
        to_borrower=False,
    )


def send_upload_contract_notification_to_lender(ses: SESClient, application: Application) -> str:
    """
    Sends an email to the lender to notify them of a new contract submission.

    This function generates an email message for the lender associated with
    the application, notifying them that a new contract has been submitted and needs their review.
    The email contains a link to login and review the contract.
    """
    return send_email(
        ses,
        get_lender_emails(application.lender, MessageType.CONTRACT_UPLOAD_CONFIRMATION_TO_FI),
        get_template_data(
            "New_contract_submission",
            _("New contract submission"),
            {
                "LOGIN_URL": f"{app_settings.frontend_url}/login",
            },
        ),
        to_borrower=False,
    )


def send_upload_contract_confirmation(ses: SESClient, application: Application) -> str:
    """
    Sends an email to the borrower confirming the successful upload of the contract.

    This function generates an email message for the borrower associated with the application,
    confirming that their contract has been successfully uploaded.
    """
    return send_email(
        ses,
        [application.primary_email],
        get_template_data(
            "Contract_upload_confirmation",
            _("Thank you for uploading the signed contract"),
            {
                "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
                "TENDER_TITLE": application.award.title,
                "BUYER_NAME": application.award.buyer_name,
            },
        ),
    )


def send_new_email_confirmation(
    ses: SESClient, application: Application, new_email: str, confirmation_email_token: str
) -> str:
    """
    Sends an email to confirm the new primary email for the borrower.

    This function generates and sends an email message to the new and old email addresses,
    providing a link for the user to confirm the email change.

    :param new_email: The new email address to be set as the primary email.
    :param confirmation_email_token: The token generated for confirming the email change.
    """
    data = get_template_data(
        "Confirm_email_address_change",
        _("Confirm email address change"),
        {
            "NEW_MAIL": new_email,
            "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
            "CONFIRM_EMAIL_CHANGE_URL": (
                f"{app_settings.frontend_url}/application/{quote(application.uuid)}/change-primary-email"
                f"?token={quote(confirmation_email_token)}"
            ),
        },
    )

    send_email(ses, application.primary_email, data)
    return send_email(ses, [new_email], data)


def send_mail_to_reset_password(ses: SESClient, username: str, temporary_password: str) -> str:
    """
    Sends an email to a user with instructions to reset their password.

    This function generates and sends an email message to a user providing a link
    for them to reset their password.

    :param username: The username associated with the account for which the password is to be reset.
    :param temporary_password: A temporary password generated for the account.
    """
    return send_email(
        ses,
        [username],
        get_template_data(
            "Reset_password",
            _("Reset password"),
            {
                "USER_ACCOUNT": username,
                "RESET_PASSWORD_URL": (
                    f"{app_settings.frontend_url}/create-password"
                    f"?key={quote(temporary_password)}&email={quote(username)}"
                ),
            },
        ),
        to_borrower=False,
    )


def get_invitation_email_parameters(application: Application) -> dict[str, str]:
    base_application_url = f"{app_settings.frontend_url}/application/{quote(application.uuid)}"
    base_fathom_url = "?utm_source=credere-intro&utm_medium=email&utm_campaign="
    return {
        "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
        "TENDER_TITLE": application.award.title,
        "BUYER_NAME": application.award.buyer_name,
        "FIND_OUT_MORE_URL": f"{base_application_url}/intro{base_fathom_url}intro",
        "REMOVE_ME_URL": f"{base_application_url}/decline{base_fathom_url}decline",
    }


def send_invitation_email(ses: SESClient, application: Application) -> str:
    """
    Sends an invitation email to the provided email address.

    This function sends an email containing an invitation to the recipient to join a credit scheme.
    It also provides options to find out more or to decline the invitation.
    """
    return send_email(
        ses,
        [application.primary_email],
        get_template_data(
            "Access_to_credit_scheme_for_MSMEs",
            _("Opportunity to access MSME credit for being awarded a public contract"),
            get_invitation_email_parameters(application),
        ),
    )


def send_mail_intro_reminder(ses: SESClient, application: Application) -> str:
    """
    Sends an introductory reminder email to the provided email address.

    This function sends a reminder email to the recipient about an invitation to join a credit scheme.
    The email also provides options to find out more or to decline the invitation.
    """
    return send_email(
        ses,
        [application.primary_email],
        get_template_data(
            "Access_to_credit_reminder",
            _("Opportunity to access MSME credit for being awarded a public contract"),
            get_invitation_email_parameters(application),
        ),
    )


def send_mail_submit_reminder(ses: SESClient, application: Application) -> str:
    """
    Sends a submission reminder email to the provided email address.

    This function sends a reminder email to the recipient about a pending credit scheme application.
    The email also provides options to apply for the credit or to decline the application.
    """
    return send_email(
        ses,
        [application.primary_email],
        get_template_data(
            "Complete_application_reminder",
            _("Reminder - Opportunity to access MSME credit for being awarded a public contract"),
            {
                "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
                "TENDER_TITLE": application.award.title,
                "BUYER_NAME": application.award.buyer_name,
                "APPLY_FOR_CREDIT_URL": f"{app_settings.frontend_url}/application/{quote(application.uuid)}/intro",
                "REMOVE_ME_URL": f"{app_settings.frontend_url}/application/{quote(application.uuid)}/decline",
            },
        ),
    )


def send_notification_new_app_to_lender(ses: SESClient, lender: Lender) -> str:
    """
    Sends a notification email about a new application to a lender's email group.

    :param lender: The lender to email.
    """
    return send_email(
        ses,
        get_lender_emails(lender, MessageType.NEW_APPLICATION_FI),
        get_template_data(
            "FI_New_application_submission_FI_user",
            _("New application submission"),
            {
                "LOGIN_URL": f"{app_settings.frontend_url}/login",
            },
        ),
        to_borrower=False,
    )


def send_notification_new_app_to_ocp(ses: SESClient, application: Application) -> str:
    """
    Sends a notification email about a new application to the Open Contracting Partnership's (OCP) email group.
    """
    return send_email(
        ses,
        [app_settings.ocp_email_group],
        get_template_data(
            "New_application_submission_OCP_user",
            _("New application submission"),
            {
                "LENDER_NAME": application.lender.name,
                "LOGIN_URL": f"{app_settings.frontend_url}/login",
            },
        ),
        to_borrower=False,
    )


def send_mail_request_to_borrower(ses: SESClient, application: Application, email_message: str) -> str:
    """
    Sends an email request to the borrower for additional data.

    :param email_message: Message content from the lender to be included in the email.
    """
    return send_email(
        ses,
        [application.primary_email],
        get_template_data(
            "Request_data_to_SME",
            _("New message from a financial institution"),
            {
                "LENDER_NAME": application.lender.name,
                "LENDER_MESSAGE": email_message,
                "LOGIN_DOCUMENTS_URL": f"{app_settings.frontend_url}/application/{quote(application.uuid)}/documents",
            },
        ),
    )


def send_overdue_application_email_to_lender(ses: SESClient, lender: Lender, amount: int) -> str:
    """
    Sends an email notification to the lender about overdue applications.

    :param lender: The overdue lender.
    :param amount: Number of overdue applications.
    """
    return send_email(
        ses,
        get_lender_emails(lender, MessageType.OVERDUE_APPLICATION),
        get_template_data(
            "Overdue_application_FI",
            _("You have credit applications that need processing"),
            {
                "USER": lender.name,
                "NUMBER_APPLICATIONS": amount,
                "LOGIN_URL": f"{app_settings.frontend_url}/login",
            },
        ),
        to_borrower=False,
    )


def send_overdue_application_email_to_ocp(ses: SESClient, application: Application) -> str:
    """
    Sends an email notification to the Open Contracting Partnership (OCP) about overdue applications.
    """
    return send_email(
        ses,
        [app_settings.ocp_email_group],
        get_template_data(
            "Overdue_application_OCP_admin",
            _("New overdue application"),
            {
                "USER": application.lender.name,
                "LENDER_NAME": application.lender.name,
                "LOGIN_URL": f"{app_settings.frontend_url}/login",
            },
        ),
        to_borrower=False,
    )


def send_rejected_application_email(ses: SESClient, application: Application) -> str:
    """
    Sends an email notification to the applicant when an application has been rejected.
    """
    return send_email(
        ses,
        [application.primary_email],
        get_template_data(
            "Application_declined",
            _("Your credit application has been declined"),
            {
                "LENDER_NAME": application.lender.name,
                "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
                "FIND_ALTENATIVE_URL": (
                    f"{app_settings.frontend_url}/application/{quote(application.uuid)}/find-alternative-credit"
                ),
            },
        ),
    )


def send_rejected_application_email_without_alternatives(ses: SESClient, application: Application) -> str:
    """
    Sends an email notification to the applicant when an application has been rejected,
    and no alternatives are available.
    """
    return send_email(
        ses,
        [application.primary_email],
        get_template_data(
            "Application_declined_without_alternative",
            _("Your credit application has been declined"),
            {
                "LENDER_NAME": application.lender.name,
                "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
            },
        ),
    )


def send_copied_application_notification_to_borrower(ses: SESClient, application: Application) -> str:
    """
    Sends an email notification to the borrower when an application
    has been copied, allowing them to continue with the application process.
    """
    return send_email(
        ses,
        [application.primary_email],
        get_template_data(
            "alternative_credit_msme",
            _("Alternative credit option"),
            {
                "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
                "CONTINUE_URL": f"{app_settings.frontend_url}/application/{application.uuid}/credit-options",
            },
        ),
    )


def send_upload_documents_notifications_to_lender(ses: SESClient, application: Application) -> str:
    """
    Sends an email notification to the lender to notify them that new
    documents have been uploaded and are ready for their review.
    """
    return send_email(
        ses,
        get_lender_emails(application.lender, MessageType.BORROWER_DOCUMENT_UPDATED),
        get_template_data(
            "FI_Documents_Updated_FI_user",
            _("Application updated"),
            {
                "LOGIN_URL": f"{app_settings.frontend_url}/login",
            },
        ),
        to_borrower=False,
    )
