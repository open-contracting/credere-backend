import json
import logging
import os
from pathlib import Path
from urllib.parse import quote

from app.schema.core import Application
from app.settings import app_settings

logger = logging.getLogger(__name__)

BASE_TEMPLATES_PATH = os.path.join(Path(__file__).absolute().parent.parent, "email_templates")

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
        "en": "Your credit application has been pre-approved",
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


def set_destinations(email: str, to_msme=True):
    """
    Sets the email destination for the application based on the environment.

    This function checks if the application is running in the 'production' environment.
    If it is, it returns the email passed as the parameter to the function.
    If it's not in 'production' environment, it returns the test email receiver set in the application settings.

    :param email: The email to be set as destination.
    :type email: str

    :param to_msme: If the email is for an MSME.
    :type email: boolean

    :return: Returns the destination email.
    :rtype: str
    """
    if app_settings.environment == "production" or not to_msme:
        return email
    return app_settings.test_mail_receiver


def generate_common_data():
    """
    Generates a dictionary containing common data used in the application.

    This function pulls various URLs and images from the application settings, such as the frontend URL and
    the URLs of various logos and social media links. This data is used in the application for rendering emails.

    :return: Returns a dictionary containing the frontend URL, URLs of various logos and social media links.
    :rtype: dict
    """

    return {
        "OCP_LOGO": app_settings.images_base_url + "/logoocp.jpg",
        "TWITTER_LOGO": app_settings.images_base_url + "/twiterlogo.png",
        "FB_LOGO": app_settings.images_base_url + "/facebook.png",
        "LINK_LOGO": app_settings.images_base_url + "/link.png",
        "STRIVE_LOGO": app_settings.images_base_url + "/strive_logo_lockup_horizontal_positive.png",
        "TWITTER_LINK": app_settings.twitter_link,
        "FACEBOOK_LINK": app_settings.facebook_link,
        "LINK_LINK": app_settings.link_link,
    }


def get_images_base_url():
    """
    Generates the base URL for images.

    This function pulls the base URL for images from the application settings and
    appends a subpath if it exists. The subpath is used for localization based on user language.

    :return: Returns the base URL for images.
    :rtype: str
    """

    images_base_url = app_settings.images_base_url
    if app_settings.email_template_lang != "":
        images_base_url = f"{images_base_url}/{app_settings.email_template_lang}"

    return images_base_url


def prepare_html(template_name, parameters):
    """
    Reads the content of the file in template_name, replace its parameters, and prepare the rest of the main
    parameters and Subject to send the email via AWS.
    """
    subject = f"Credere - {TEMPLATE_FILES[template_name][app_settings.email_template_lang]}"
    if app_settings.email_template_lang == "es":
        template_name = f"{template_name}_es"
    template_name = f"{template_name}.html"
    with open(os.path.join(BASE_TEMPLATES_PATH, template_name), encoding="utf-8") as f:
        html = f.read()
    for key in parameters.keys():
        to_replace = "{{" + key + "}}"
        html = html.replace(to_replace, str(parameters[key]))
    data = {
        **generate_common_data(),
        "CONTENT": html,
        "SUBJECT": f"{subject}",
    }
    return data


def send_email(ses, email, data, to_msme=True):
    email = email.strip()
    if not email:
        logger.warning(f"{app_settings.environment} - Skipping empty email address")
        return ""

    destinations = set_destinations(email, to_msme)

    logger.info(f"{app_settings.environment} - Email to: {email} sent to {destinations}")
    response = ses.send_templated_email(
        Source=app_settings.email_sender_address,
        Destination={"ToAddresses": [destinations]},
        Template=f"credere-main-{app_settings.email_template_lang}",
        TemplateData=json.dumps(data),
    )

    return response.get("MessageId")


def send_application_approved_email(ses, application: Application):
    """
    Sends an email notification when an application has been approved.

    This function generates an email message with the application details and a
    link to upload the contract. The email is sent to the primary email address associated
    with the application. The function utilizes the SES (Simple Email Service) client to send the email.

    :param ses: SES client instance used to send emails.
    :type ses: botocore.client.SES
    :param application: The application object which has been approved.
    :type application: Application
    """

    images_base_url = get_images_base_url()
    html_data = {
        "FI": application.lender.name,
        "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
        "TENDER_TITLE": application.award.title,
        "BUYER_NAME": application.award.buyer_name,
        "UPLOAD_CONTRACT_URL": f"{app_settings.frontend_url}/application/{quote(application.uuid)}/upload-contract",
        "UPLOAD_CONTRACT_IMAGE_LINK": f"{images_base_url}/uploadContract.png",
    }
    data = prepare_html("Application_approved", html_data)

    send_email(ses, application.primary_email, data)


def send_application_submission_completed(ses, application: Application):
    """
    Sends an email notification when an application is submitted.

    The email is sent to the primary email address associated
    with the application. The function utilizes the SES (Simple Email Service) client to send the email.

    :param ses: SES client instance used to send emails.
    :type ses: botocore.client.SES
    :param application: The application object which has been approved.
    :type application: Application
    """
    html_data = {
        "FI": application.lender.name,
        "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
    }

    send_email(ses, application.primary_email, prepare_html("Application_submitted", html_data))


def send_application_credit_disbursed(ses, application: Application):
    """
    Sends an email notification when an application has the credit dibursed.

    The email is sent to the primary email address associated
    with the application. The function utilizes the SES (Simple Email Service) client to send the email.

    :param ses: SES client instance used to send emails.
    :type ses: botocore.client.SES
    :param application: The application object which has been approved.
    :type application: Application
    """
    html_data = {
        "FI": application.lender.name,
        "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
        "FI_EMAIL": application.lender.email_group,
    }

    send_email(
        ses,
        application.primary_email,
        prepare_html("Application_credit_disbursed", html_data),
    )


def send_mail_to_new_user(ses, name, username, temp_password):
    """
    Sends an email to a new user with a link to set their password.

    This function generates an email message for new users, providing them with
    a temporary password and a link to set their password. The email is sent to the
    username (which is an email address) provided.

    :param ses: SES client instance used to send emails.
    :type ses: botocore.client.SES
    :param name: The name of the new user.
    :type name: str
    :param username: The username (email address) of the new user.
    :type username: str
    :param temp_password: The temporary password for the new user.
    :type temp_password: str
    """

    images_base_url = get_images_base_url()

    html_data = {
        "USER": name,
        "SET_PASSWORD_IMAGE_LINK": f"{images_base_url}/set_password.png",
        "LOGIN_URL": app_settings.frontend_url
        + "/create-password?key="
        + quote(temp_password)
        + "&email="
        + quote(username),
    }

    send_email(ses, username, prepare_html("New_Account_Created", html_data), False)


def send_upload_contract_notification_to_FI(ses, application):
    """
    Sends an email to the Financial Institution (FI) to notify them of a new contract submission.

    This function generates an email message for the Financial Institution (FI) associated with
    the application, notifying them that a new contract has been submitted and needs their review.
    The email contains a link to login and review the contract.

    :param ses: SES client instance used to send emails.
    :type ses: botocore.client.SES
    :param application: The application associated with the contract.
    :type application: core.Application
    """

    images_base_url = get_images_base_url()

    html_data = {
        "LOGIN_URL": app_settings.frontend_url + "/login",
        "LOGIN_IMAGE_LINK": images_base_url + "/logincompleteimage.png",
    }

    send_email(
        ses,
        application.lender.email_group,
        prepare_html("New_contract_submission", html_data),
        False,
    )


def send_upload_contract_confirmation(ses, application):
    """
    Sends an email to the borrower confirming the successful upload of the contract.

    This function generates an email message for the borrower associated with the application,
    confirming that their contract has been successfully uploaded.

    :param ses: SES client instance used to send emails.
    :type ses: botocore.client.SES
    :param application: The application associated with the contract.
    :type application: core.Application
    """

    html_data = {
        "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
        "TENDER_TITLE": application.award.title,
        "BUYER_NAME": application.award.buyer_name,
    }

    send_email(
        ses,
        application.lender.email_group,
        prepare_html("Contract_upload_confirmation", html_data),
        False,
    )


def send_new_email_confirmation(
    ses,
    borrower_name: str,
    new_email: str,
    old_email: str,
    confirmation_email_token: str,
    application_uuid: str,
):
    """
    Sends an email to confirm the new primary email for the borrower.

    This function generates and sends an email message to the new and old email addresses,
    providing a link for the user to confirm the email change.

    :param ses: SES client instance used to send emails.
    :type ses: botocore.client.SES
    :param borrower_name: The name of the borrower associated with the application.
    :type borrower_name: str
    :param new_email: The new email address to be set as the primary email.
    :type new_email: str
    :param old_email: The current primary email address.
    :type old_email: str
    :param confirmation_email_token: The token generated for confirming the email change.
    :type confirmation_email_token: str
    :param application_uuid: The unique identifier for the application.
    :type application_uuid: str
    :return: The ID of the sent message.
    :rtype: str
    """

    images_base_url = get_images_base_url()
    confirm_email_change_url = (
        app_settings.frontend_url
        + "/application/"
        + quote(application_uuid)
        + "/change-primary-email?token="
        + quote(confirmation_email_token)
    )
    html_data = {
        "NEW_MAIL": new_email,
        "AWARD_SUPPLIER_NAME": borrower_name,
        "CONFIRM_EMAIL_CHANGE_URL": confirm_email_change_url,
        "CONFIRM_EMAIL_CHANGE_IMAGE_LINK": images_base_url + "/confirmemailchange.png",
    }

    new_email_address = set_destinations(new_email)
    old_email_address = set_destinations(old_email)

    data = prepare_html("Confirm_email_address_change", html_data)

    response = send_email(ses, new_email_address, data)
    send_email(ses, old_email_address, data)

    return response


def send_mail_to_reset_password(ses, username: str, temp_password: str):
    """
    Sends an email to a user with instructions to reset their password.

    This function generates and sends an email message to a user providing a link
    for them to reset their password.

    :param ses: SES client instance used to send emails.
    :type ses: botocore.client.SES
    :param username: The username associated with the account for which the password is to be reset.
    :type username: str
    :param temp_password: A temporary password generated for the account.
    :type temp_password: str
    """

    images_base_url = get_images_base_url()

    html_data = {
        "USER_ACCOUNT": username,
        "RESET_PASSWORD_URL": app_settings.frontend_url
        + "/create-password?key="
        + quote(temp_password)
        + "&email="
        + quote(username),
        "RESET_PASSWORD_IMAGE": images_base_url + "/ResetPassword.png",
    }

    send_email(ses, username, prepare_html("Reset_password", html_data), False)


def send_invitation_email(ses, uuid, email, borrower_name, buyer_name, tender_title):
    """
    Sends an invitation email to the provided email address.

    This function sends an email containing an invitation to the recipient to join a credit scheme.
    It also provides options to find out more or to decline the invitation.

    :param ses: SES client instance used to send emails.
    :type ses: botocore.client.SES
    :param uuid: Unique identifier associated with the application.
    :type uuid: str
    :param email: Email address of the recipient.
    :type email: str
    :param borrower_name: The name of the borrower.
    :type borrower_name: str
    :param buyer_name: The name of the buyer.
    :type buyer_name: str
    :param tender_title: The title of the tender.
    :type tender_title: str

    :return: The MessageId of the sent email.
    :rtype: str
    """

    images_base_url = get_images_base_url()

    html_data = {
        "AWARD_SUPPLIER_NAME": borrower_name,
        "TENDER_TITLE": tender_title,
        "BUYER_NAME": buyer_name,
        "FIND_OUT_MORE_IMAGE_LINK": f"{images_base_url}/findoutmore.png",
        "REMOVE_ME_IMAGE_LINK": f"{images_base_url}/removeme.png",
        "FIND_OUT_MORE_URL": f"{app_settings.frontend_url}/application/{quote(uuid)}/intro",
        "REMOVE_ME_URL": f"{app_settings.frontend_url}/application/{quote(uuid)}/decline",
    }

    return send_email(ses, email, prepare_html("Access_to_credit_scheme_for_MSMEs", html_data))


def send_mail_intro_reminder(ses, uuid, email, borrower_name, buyer_name, tender_title):
    """
    Sends an introductory reminder email to the provided email address.

    This function sends a reminder email to the recipient about an invitation to join a credit scheme.
    The email also provides options to find out more or to decline the invitation.

    :param ses: SES client instance used to send emails.
    :type ses: botocore.client.SES
    :param uuid: Unique identifier associated with the application.
    :type uuid: str
    :param email: Email address of the recipient.
    :type email: str
    :param borrower_name: The name of the borrower.
    :type borrower_name: str
    :param buyer_name: The name of the buyer.
    :type buyer_name: str
    :param tender_title: The title of the tender.
    :type tender_title: str

    :return: The MessageId of the sent email.
    :rtype: str
    """

    images_base_url = get_images_base_url()

    html_data = {
        "AWARD_SUPPLIER_NAME": borrower_name,
        "TENDER_TITLE": tender_title,
        "BUYER_NAME": buyer_name,
        "FIND_OUT_MORE_URL": app_settings.frontend_url + "/application/" + quote(uuid) + "/intro",
        "FIND_OUT_MORE_IMAGE_LINK": images_base_url + "/findoutmore.png",
        "REMOVE_ME_IMAGE_LINK": images_base_url + "/removeme.png",
        "REMOVE_ME_URL": f"{app_settings.frontend_url}/application/{quote(uuid)}/decline",
    }

    return send_email(ses, email, prepare_html("Access_to_credit_scheme_for_MSMEs", html_data))


def send_mail_submit_reminder(ses, uuid, email, borrower_name, buyer_name, tender_title):
    """
    Sends a submission reminder email to the provided email address.

    This function sends a reminder email to the recipient about a pending credit scheme application.
    The email also provides options to apply for the credit or to decline the application.

    :param ses: SES client instance used to send emails.
    :type ses: botocore.client.SES
    :param uuid: Unique identifier associated with the application.
    :type uuid: str
    :param email: Email address of the recipient.
    :type email: str
    :param borrower_name: The name of the borrower.
    :type borrower_name: str
    :param buyer_name: The name of the buyer.
    :type buyer_name: str
    :param tender_title: The title of the tender.
    :type tender_title: str

    :return: The MessageId of the sent email.
    :rtype: str"""
    images_base_url = get_images_base_url()
    html_data = {
        "AWARD_SUPPLIER_NAME": borrower_name,
        "TENDER_TITLE": tender_title,
        "BUYER_NAME": buyer_name,
        "APPLY_FOR_CREDIT_URL": app_settings.frontend_url + "/application/" + quote(uuid) + "/intro",
        "APPLY_FOR_CREDIT_IMAGE_LINK": images_base_url + "/applyForCredit.png",
        "REMOVE_ME_IMAGE_LINK": images_base_url + "/removeme.png",
        "REMOVE_ME_URL": f"{app_settings.frontend_url}/application/{quote(uuid)}/decline",
    }

    return send_email(ses, email, prepare_html("Access_to_credit_reminder", html_data))


def send_notification_new_app_to_fi(ses, lender_email_group):
    """
    Sends a notification email about a new application to a financial institution's email group.

    :param ses: SES client instance used to send emails.
    :type ses: botocore.client.SES
    :param lender_email_group: List of email addresses belonging to the lender.
    :type lender_email_group: list[str]
    """
    images_base_url = get_images_base_url()

    html_data = {
        "LOGIN_URL": app_settings.frontend_url + "/login",
        "LOGIN_IMAGE_LINK": images_base_url + "/logincompleteimage.png",
    }

    send_email(
        ses,
        lender_email_group,
        prepare_html("FI_New_application_submission_FI_user", html_data),
        False,
    )


def send_notification_new_app_to_ocp(ses, ocp_email_group, lender_name):
    """
    Sends a notification email about a new application to the Open Contracting Partnership's (OCP) email group.

    :param ses: SES client instance used to send emails.
    :type ses: botocore.client.SES
    :param ocp_email_group: List of email addresses belonging to the OCP.
    :type ocp_email_group: list[str]
    :param lender_name: Name of the lender associated with the new application.
    :type lender_name: str
    """

    images_base_url = get_images_base_url()

    html_data = {
        "FI": lender_name,
        "LOGIN_URL": app_settings.frontend_url + "/login",
        "LOGIN_IMAGE_LINK": images_base_url + "/logincompleteimage.png",
    }

    send_email(
        ses,
        ocp_email_group,
        prepare_html("New_application_submission_OCP_user", html_data),
        False,
    )


def send_mail_request_to_sme(ses, uuid, lender_name, email_message, sme_email):
    """
    Sends an email request to the Small and Medium-Sized Enterprises (SME) from the lender for additional data.

    :param ses: SES client instance used to send emails.
    :type ses: botocore.client.SES
    :param uuid: Unique identifier for the application.
    :type uuid: str
    :param lender_name: Name of the lender making the request.
    :type lender_name: str
    :param email_message: Message content from the lender to be included in the email.
    :type email_message: str
    :param sme_email: Email address of the SME.
    :type sme_email: str
    :return: The unique identifier for the sent message.
    :rtype: str
    """
    images_base_url = get_images_base_url()

    html_data = {
        "FI": lender_name,
        "FI_MESSAGE": email_message,
        "LOGIN_DOCUMENTS_URL": f"{app_settings.frontend_url}/application/{quote(uuid)}/documents",
        "LOGIN_IMAGE_LINK": f"{images_base_url}/uploadDocument.png",
    }

    return send_email(ses, sme_email, prepare_html("Request_data_to_SME", html_data))


def send_overdue_application_email_to_FI(ses, name: str, email: str, amount: int):
    """
    Sends an email notification to the Financial Institution (FI) about overdue applications.

    :param ses: SES client instance used to send emails.
    :type ses: botocore.client.SES
    :param name: Name of the recipient at the FI.
    :type name: str
    :param email: Email address of the recipient at the FI.
    :type email: str
    :param amount: Number of overdue applications.
    :type amount: int
    :return: The unique identifier for the sent message.
    :rtype: str
    """

    images_base_url = get_images_base_url()

    html_data = {
        "USER": name,
        "NUMBER_APPLICATIONS": amount,
        "LOGIN_IMAGE_LINK": images_base_url + "/logincompleteimage.png",
        "LOGIN_URL": app_settings.frontend_url + "/login",
    }

    return send_email(ses, email, prepare_html("Overdue_application_FI", html_data), False)


def send_overdue_application_email_to_OCP(ses, name: str):
    """
    Sends an email notification to the Open Contracting Partnership (OCP) about overdue applications.

    :param ses: SES client instance used to send emails.
    :type ses: botocore.client.SES
    :param name: Name of the recipient at the OCP.
    :type name: str
    :return: The unique identifier for the sent message.
    :rtype: str
    """
    images_base_url = get_images_base_url()

    html_data = {
        "USER": name,
        "FI": name,
        "LOGIN_IMAGE_LINK": images_base_url + "/logincompleteimage.png",
        "LOGIN_URL": app_settings.frontend_url + "/login",
    }

    return send_email(
        ses,
        app_settings.ocp_email_group,
        prepare_html("Overdue_application_OCP_admin", html_data),
        False,
    )


def send_rejected_application_email(ses, application):
    """
    Sends an email notification to the applicant when an application has been rejected.

    :param ses: SES client instance used to send emails.
    :type ses: botocore.client.SES
    :param application: An object that contains information about the application that was rejected.
    :type application: Application
    :return: The unique identifier for the sent message.
    :rtype: str
    """
    images_base_url = get_images_base_url()

    html_data = {
        "FI": application.lender.name,
        "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
        "FIND_ALTENATIVE_URL": app_settings.frontend_url
        + f"/application/{quote(application.uuid)}/find-alternative-credit",
        "FIND_ALTERNATIVE_IMAGE_LINK": images_base_url + "/findAlternative.png",
    }
    return send_email(ses, application.primary_email, prepare_html("Application_declined", html_data))


def send_rejected_application_email_without_alternatives(ses, application):
    """
    Sends an email notification to the applicant when an application has been rejected,
    and no alternatives are available.

    :param ses: SES client instance used to send emails.
    :type ses: botocore.client.SES
    :param application: An object that contains information about the application that was rejected.
    :type application: Application
    :return: The unique identifier for the sent message.
    :rtype: str
    """

    html_data = {
        "FI": application.lender.name,
        "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
    }
    return send_email(
        ses,
        application.primary_email,
        prepare_html("Application_declined_without_alternative", html_data),
    )


def send_copied_application_notification_to_sme(ses, application):
    """
    Sends an email notification to the SME (Small and Medium-Sized Enterprises) when an application
    has been copied, allowing them to continue with the application process.

    :param ses: SES client instance used to send emails.
    :type ses: botocore.client.SES
    :param application: An object that contains information about the copied application.
    :type application: Application
    :return: The unique identifier for the sent message.
    :rtype: str
    """
    images_base_url = get_images_base_url()
    html_data = {
        "AWARD_SUPPLIER_NAME": application.borrower.legal_name,
        "CONTINUE_IMAGE_LINK": f"{images_base_url}/continueInCredere.png",
        "CONTINUE_URL": f"{app_settings.frontend_url}/application/{application.uuid}/credit-options",
    }

    return send_email(
        ses,
        application.primary_email,
        prepare_html("alternative_credit_msme", html_data),
    )


def send_upload_documents_notifications_to_FI(ses, email: str):
    """
    Sends an email notification to the Financial Institution (FI) to notify them that new
    documents have been uploaded and are ready for their review.

    :param ses: SES client instance used to send emails.
    :type ses: botocore.client.SES
    :param email: Email address of the Financial Institution to receive the notification.
    :type email: str
    :return: The unique identifier for the sent message.
    :rtype: str
    """

    images_base_url = get_images_base_url()
    html_data = {
        **generate_common_data(),
        "LOGIN_IMAGE_LINK": images_base_url + "/logincompleteimage.png",
        "LOGIN_URL": app_settings.frontend_url + "/login",
    }

    return send_email(ses, email, prepare_html("FI_Documents_Updated_FI_user", html_data), False)
