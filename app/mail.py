import json
import logging
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

from mypy_boto3_ses.client import SESClient

from app.models import Application
from app.settings import app_settings

logger = logging.getLogger(__name__)

BASE_TEMPLATES_PATH = os.path.join(Path(__file__).absolute().parent.parent, "email_templates")

LOCALIZED_IMAGES_BASE_URL = app_settings.images_base_url
if app_settings.email_template_lang != "":
    LOCALIZED_IMAGES_BASE_URL = f"{LOCALIZED_IMAGES_BASE_URL}/{app_settings.email_template_lang}"

COMMON_DATA = {
    "OCP_LOGO": f"{app_settings.images_base_url}/logoocp.jpg",
    "TWITTER_LOGO": f"{app_settings.images_base_url}/twiterlogo.png",
    "FB_LOGO": f"{app_settings.images_base_url}/facebook.png",
    "LINK_LOGO": f"{app_settings.images_base_url}/link.png",
    "STRIVE_LOGO": f"{app_settings.images_base_url}/strive_logo_lockup_horizontal_positive.png",
    "TWITTER_LINK": app_settings.twitter_link,
    "FACEBOOK_LINK": app_settings.facebook_link,
    "LINK_LINK": app_settings.link_link,
}

# Templates files names and email subject
TEMPLATE_FILES = {
    "Access_to_credit_reminder": {
        "es": "Recordatorio - Oportunidad de acceso a crédito MIPYME por ser adjudicatario de contrato estatal",
        "en": "Reminder - Opportunity to access MSME credit for being awarded a public contract",
    },
    "Access_to_credit_scheme_for_MSMEs": {
        "es": "Oportunidad de acceso a crédito MIPYME por ser adjudicatario de contrato estatal",
        "en": "Opportunity to access MSME credit for being awarded a public contract",
    },
    "alternative_credit_msme": {
        "en": "Alternative credit option",
        "es": "Opción de crédito alternativa",
    },
    "Application_approved": {
        "en": "Your credit application has been prequalified",
        "es": "Revisión de tu aplicación completada exitosamente",
    },
    "Application_credit_disbursed": {
        "en": "Your credit application has been approved",
        "es": "Tu solicitud de crédito ha sido aprobada",
    },
    "Application_declined": {
        "en": "Your credit application has been declined",
        "es": "Tu solicitud de crédito ha sido rechazada",
    },
    "Application_declined_without_alternative": {
        "en": "Your credit application has been declined",
        "es": "Tu solicitud de crédito ha sido rechazada",
    },
    "Application_submitted": {
        "en": "Application Submission Complete",
        "es": "Envío de aplicación completada",
    },
    "Complete_application_reminder": {
        "en": "Complete your credit application",
        "es": "Completa tu solicitud de crédito",
    },
    "Confirm_email_address_change": {
        "en": "Confirm email address change",
        "es": "Confirmar cambio de dirección de correo electrónico",
    },
    "Contract_upload_confirmation": {
        "en": "Thank you for uploading the signed contract",
        "es": "Gracias por subir tu contrato firmado",
    },
    "Credit_application_submitted": {
        "en": "Your credit application has been submitted",
        "es": "Tu solicitud de crédito ha sido enviada",
    },
    "FI_Documents_Updated_FI_user": {
        "en": "Application updated",
        "es": "Aplicación actualizada",
    },
    "FI_New_application_submission_FI_user": {
        "en": "New application submission",
        "es": "Nueva aplicación recibida",
    },
    "New_Account_Created": {"en": "Welcome", "es": "Bienvenido/a"},
    "New_application_submission_OCP_user": {
        "en": "New application submission",
        "es": "Nueva aplicación recibida",
    },
    "New_contract_submission": {
        "en": "New contract submission",
        "es": "Una MIPYME ha subido su contrato",
    },
    "Overdue_application_FI": {
        "en": "You have credit applications that need processing",
        "es": "Tienes solicitudes de crédito que necesitan procesamiento",
    },
    "Overdue_application_OCP_admin": {
        "en": "New overdue application",
        "es": "Nueva solicitud vencida",
    },
    "Request_data_to_SME": {
        "en": "New message from a financial institution",
        "es": "Nuevo mensaje de una institución financiera",
    },
    "Reset_password": {"en": "Reset password", "es": "Restablecer contraseña"},
    "Upload_contract": {
        "en": "Please upload your contract",
        "es": "Por favor sube tu contrato",
    },
}


def set_destinations(email: str, to_borrower: bool = True) -> str:
    """
    Sets the email destination for the application based on the environment.

    This function checks if the application is running in the 'production' environment.
    If it is, it returns the email passed as the parameter to the function.
    If it's not in 'production' environment, it returns the test email receiver set in the application settings.

    :param email: The email to be set as destination.
    :param to_borrower: If the email is for a borrower.
    :return: Returns the destination email.
    """
    if app_settings.environment == "production" or not to_borrower:
        return email
    return app_settings.test_mail_receiver


def prepare_html(template_name: str, parameters: dict[str, Any]) -> dict[str, str]:
    """
    Reads the content of the file in template_name, replace its parameters, and prepare the rest of the main
    parameters and Subject to send the email via AWS.
    """
    with open(
        os.path.join(
            BASE_TEMPLATES_PATH, f"{template_name}{'_es' if app_settings.email_template_lang == 'es' else ''}.html"
        ),
        encoding="utf-8",
    ) as f:
        html = f.read()

    for key in parameters.keys():
        html = html.replace("{{%s}}" % key, str(parameters[key]))

    return {
        **COMMON_DATA,
        "CONTENT": html,
        "SUBJECT": f"Credere - {TEMPLATE_FILES[template_name][app_settings.email_template_lang]}",
    }


def send_email(ses: SESClient, email: str, data: dict[str, str], to_borrower: bool = True) -> str:
    destinations = set_destinations(email, to_borrower)

    logger.info("%s - Email to: %s sent to %s", app_settings.environment, email, destinations)
    response = ses.send_templated_email(
        Source=app_settings.email_sender_address,
        Destination={"ToAddresses": [destinations]},
        Template=f"credere-main-{app_settings.email_template_lang}",
        TemplateData=json.dumps(data),
        ReplyToAddresses=[app_settings.ocp_email_group],
    )

    return response["MessageId"]


def send_application_approved_email(ses: SESClient, application: Application) -> str:
    """
    Sends an email notification when an application has been approved.

    This function generates an email message with the application details and a
    link to upload the contract. The email is sent to the primary email address associated
    with the application. The function utilizes the SES (Simple Email Service) client to send the email.
    """
    html_data = {
        "FI": application.lender.name,
        "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
        "TENDER_TITLE": application.award.title,
        "BUYER_NAME": application.award.buyer_name,
        "UPLOAD_CONTRACT_URL": f"{app_settings.frontend_url}/application/{quote(application.uuid)}/upload-contract",
        "UPLOAD_CONTRACT_IMAGE_LINK": f"{LOCALIZED_IMAGES_BASE_URL}/uploadContract.png",
    }

    if application.lender.default_pre_approval_message:
        html_data["ADDITIONAL_COMMENTS"] = application.lender.default_pre_approval_message
    elif (
        "additional_comments" in application.lender_approved_data
        and application.lender_approved_data["additional_comments"]
    ):
        html_data["ADDITIONAL_COMMENTS"] = application.lender_approved_data["additional_comments"]
    else:
        html_data["ADDITIONAL_COMMENTS"] = "Ninguno"

    return send_email(ses, application.primary_email, prepare_html("Application_approved", html_data))


def send_application_submission_completed(ses: SESClient, application: Application) -> str:
    """
    Sends an email notification when an application is submitted.

    The email is sent to the primary email address associated
    with the application. The function utilizes the SES (Simple Email Service) client to send the email.
    """
    return send_email(
        ses,
        application.primary_email,
        prepare_html(
            "Application_submitted",
            {
                "FI": application.lender.name,
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
        application.primary_email,
        prepare_html(
            "Application_credit_disbursed",
            {
                "FI": application.lender.name,
                "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
                "FI_EMAIL": application.lender.email_group,
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
        username,
        prepare_html(
            "New_Account_Created",
            {
                "USER": name,
                "SET_PASSWORD_IMAGE_LINK": f"{LOCALIZED_IMAGES_BASE_URL}/set_password.png",
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
        application.lender.email_group,
        prepare_html(
            "New_contract_submission",
            {
                "LOGIN_URL": f"{app_settings.frontend_url}/login",
                "LOGIN_IMAGE_LINK": f"{LOCALIZED_IMAGES_BASE_URL}/logincompleteimage.png",
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
        application.primary_email,
        prepare_html(
            "Contract_upload_confirmation",
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
    data = prepare_html(
        "Confirm_email_address_change",
        {
            "NEW_MAIL": new_email,
            "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
            "CONFIRM_EMAIL_CHANGE_URL": (
                f"{app_settings.frontend_url}/application/{quote(application.uuid)}/change-primary-email"
                f"?token={quote(confirmation_email_token)}"
            ),
            "CONFIRM_EMAIL_CHANGE_IMAGE_LINK": f"{LOCALIZED_IMAGES_BASE_URL}/confirmemailchange.png",
        },
    )

    send_email(ses, application.primary_email, data)
    return send_email(ses, new_email, data)


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
        username,
        prepare_html(
            "Reset_password",
            {
                "USER_ACCOUNT": username,
                "RESET_PASSWORD_URL": (
                    f"{app_settings.frontend_url}/create-password"
                    f"?key={quote(temporary_password)}&email={quote(username)}"
                ),
                "RESET_PASSWORD_IMAGE": f"{LOCALIZED_IMAGES_BASE_URL}/ResetPassword.png",
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
        "FIND_OUT_MORE_IMAGE_LINK": f"{LOCALIZED_IMAGES_BASE_URL}/findoutmore.png",
        "REMOVE_ME_IMAGE_LINK": f"{LOCALIZED_IMAGES_BASE_URL}/removeme.png",
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
        application.primary_email,
        prepare_html("Access_to_credit_scheme_for_MSMEs", get_invitation_email_parameters(application)),
    )


def send_mail_intro_reminder(ses: SESClient, application: Application) -> str:
    """
    Sends an introductory reminder email to the provided email address.

    This function sends a reminder email to the recipient about an invitation to join a credit scheme.
    The email also provides options to find out more or to decline the invitation.
    """
    return send_email(
        ses,
        application.primary_email,
        prepare_html("Access_to_credit_scheme_for_MSMEs", get_invitation_email_parameters(application)),
    )


def send_mail_submit_reminder(ses: SESClient, application: Application) -> str:
    """
    Sends a submission reminder email to the provided email address.

    This function sends a reminder email to the recipient about a pending credit scheme application.
    The email also provides options to apply for the credit or to decline the application.
    """
    return send_email(
        ses,
        application.primary_email,
        prepare_html(
            "Access_to_credit_reminder",
            {
                "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
                "TENDER_TITLE": application.award.title,
                "BUYER_NAME": application.award.buyer_name,
                "APPLY_FOR_CREDIT_URL": f"{app_settings.frontend_url}/application/{quote(application.uuid)}/intro",
                "APPLY_FOR_CREDIT_IMAGE_LINK": f"{LOCALIZED_IMAGES_BASE_URL}/applyForCredit.png",
                "REMOVE_ME_IMAGE_LINK": f"{LOCALIZED_IMAGES_BASE_URL}/removeme.png",
                "REMOVE_ME_URL": f"{app_settings.frontend_url}/application/{quote(application.uuid)}/decline",
            },
        ),
    )


def send_notification_new_app_to_lender(ses: SESClient, lender_email_group: str) -> str:
    """
    Sends a notification email about a new application to a lender's email group.

    :param lender_email_group: List of email addresses belonging to the lender.
    """
    return send_email(
        ses,
        lender_email_group,
        prepare_html(
            "FI_New_application_submission_FI_user",
            {
                "LOGIN_URL": f"{app_settings.frontend_url}/login",
                "LOGIN_IMAGE_LINK": f"{LOCALIZED_IMAGES_BASE_URL}/logincompleteimage.png",
            },
        ),
        to_borrower=False,
    )


def send_notification_new_app_to_ocp(ses: SESClient, lender_name: str) -> str:
    """
    Sends a notification email about a new application to the Open Contracting Partnership's (OCP) email group.

    :param lender_name: Name of the lender associated with the new application.
    """
    return send_email(
        ses,
        app_settings.ocp_email_group,
        prepare_html(
            "New_application_submission_OCP_user",
            {
                "FI": lender_name,
                "LOGIN_URL": f"{app_settings.frontend_url}/login",
                "LOGIN_IMAGE_LINK": f"{LOCALIZED_IMAGES_BASE_URL}/logincompleteimage.png",
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
        application.primary_email,
        prepare_html(
            "Request_data_to_SME",
            {
                "FI": application.lender.name,
                "FI_MESSAGE": email_message,
                "LOGIN_DOCUMENTS_URL": f"{app_settings.frontend_url}/application/{quote(application.uuid)}/documents",
                "LOGIN_IMAGE_LINK": f"{LOCALIZED_IMAGES_BASE_URL}/uploadDocument.png",
            },
        ),
    )


def send_overdue_application_email_to_lender(ses: SESClient, lender_name: str, lender_email: str, amount: int) -> str:
    """
    Sends an email notification to the lender about overdue applications.

    :param lender_name: Name of the recipient at the lender.
    :param lender_email: Email address of the recipient at the lender.
    :param amount: Number of overdue applications.
    """
    return send_email(
        ses,
        lender_email,
        prepare_html(
            "Overdue_application_FI",
            {
                "USER": lender_name,
                "NUMBER_APPLICATIONS": amount,
                "LOGIN_IMAGE_LINK": f"{LOCALIZED_IMAGES_BASE_URL}/logincompleteimage.png",
                "LOGIN_URL": f"{app_settings.frontend_url}/login",
            },
        ),
        to_borrower=False,
    )


def send_overdue_application_email_to_ocp(ses: SESClient, name: str) -> str:
    """
    Sends an email notification to the Open Contracting Partnership (OCP) about overdue applications.

    :param name: Name of the recipient at the OCP.
    """
    return send_email(
        ses,
        app_settings.ocp_email_group,
        prepare_html(
            "Overdue_application_OCP_admin",
            {
                "USER": name,
                "FI": name,
                "LOGIN_IMAGE_LINK": f"{LOCALIZED_IMAGES_BASE_URL}/logincompleteimage.png",
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
        application.primary_email,
        prepare_html(
            "Application_declined",
            {
                "FI": application.lender.name,
                "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
                "FIND_ALTENATIVE_URL": (
                    f"{app_settings.frontend_url}/application/{quote(application.uuid)}/find-alternative-credit"
                ),
                "FIND_ALTERNATIVE_IMAGE_LINK": f"{LOCALIZED_IMAGES_BASE_URL}/findAlternative.png",
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
        application.primary_email,
        prepare_html(
            "Application_declined_without_alternative",
            {
                "FI": application.lender.name,
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
        application.primary_email,
        prepare_html(
            "alternative_credit_msme",
            {
                "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
                "CONTINUE_IMAGE_LINK": f"{LOCALIZED_IMAGES_BASE_URL}/continueInCredere.png",
                "CONTINUE_URL": f"{app_settings.frontend_url}/application/{application.uuid}/credit-options",
            },
        ),
    )


def send_upload_documents_notifications_to_lender(ses: SESClient, lender_email: str) -> str:
    """
    Sends an email notification to the lender to notify them that new
    documents have been uploaded and are ready for their review.

    :param lender_email: Email address of the lender to receive the notification.
    """
    return send_email(
        ses,
        lender_email,
        prepare_html(
            "FI_Documents_Updated_FI_user",
            {
                **COMMON_DATA,
                "LOGIN_IMAGE_LINK": f"{LOCALIZED_IMAGES_BASE_URL}/logincompleteimage.png",
                "LOGIN_URL": f"{app_settings.frontend_url}/login",
            },
        ),
        to_borrower=False,
    )
