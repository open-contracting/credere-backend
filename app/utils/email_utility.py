import json
from urllib.parse import quote

import app.email_templates as email_templates
from app.core.settings import app_settings


def generate_common_data():
    return {
        "LINK-TO-WEB-VERSION": app_settings.frontend_url,
        "OCP_LOGO": app_settings.images_base_url + "/logoocp.jpg",
        "TWITTER_LOGO": app_settings.images_base_url + "/twiterlogo.png",
        "FB_LOGO": app_settings.images_base_url + "/facebook.png",
        "LINK_LOGO": app_settings.images_base_url + "/link.png",
        "TWITTER_LINK": app_settings.twitter_link,
        "FACEBOOK_LINK": app_settings.facebook_link,
        "LINK_LINK": app_settings.link_link,
    }


def get_images_base_url():
    # todo refactor required when this function receives the user language

    images_base_url = app_settings.images_base_url
    if app_settings.images_lang_subpath != "":
        images_base_url = f"{images_base_url}/{app_settings.images_lang_subpath}"

    return images_base_url


def send_mail_to_new_user(ses, name, username, temp_password):
    # todo refactor required when this function receives the user language

    images_base_url = get_images_base_url()

    data = {
        **generate_common_data(),
        "USER": name,
        "SET_PASSWORD_IMAGE_LINK": f"{images_base_url}/set_password.png",
        "LOGIN_URL": app_settings.frontend_url
        + "/create-password?key="
        + quote(temp_password)
        + "&email="
        + quote(username),
    }

    ses.send_templated_email(
        Source=app_settings.email_sender_address,
        Destination={"ToAddresses": [username]},
        Template=email_templates.NEW_USER_TEMPLATE_NAME,
        TemplateData=json.dumps(data),
    )


def send_new_email_confirmation(
    ses,
    borrower_name: str,
    new_email: str,
    old_email: str,
    confirmation_email_token: str,
    application_uuid: str,
):
    images_base_url = get_images_base_url()
    CONFIRM_EMAIL_CHANGE_URL = (
        f"{app_settings.frontend_url}/change-email/"
        f"{application_uuid}/{confirmation_email_token}/{new_email}"
    )
    data = {
        **generate_common_data(),
        "NEW_MAIL": new_email,
        "AWARD_SUPPLIER_NAME": borrower_name,
        "CONFIRM_EMAIL_CHANGE_URL": CONFIRM_EMAIL_CHANGE_URL,
        "CONFIRM_EMAIL_CHANGE_IMAGE_LINK": images_base_url + "/confirmemailchange.png",
    }

    message = ses.send_templated_email(
        Source=app_settings.email_sender_address,
        # line below needs to be changed to new_email in production to send email to proper address
        Destination={"ToAddresses": [app_settings.test_mail_receiver]},
        Template=email_templates.EMAIL_CHANGE_TEMPLATE_NAME,
        TemplateData=json.dumps(data),
    )
    ses.send_templated_email(
        Source=app_settings.email_sender_address,
        # line below needs to be changed to old_email in production to send email to proper address
        Destination={"ToAddresses": [app_settings.test_mail_receiver]},
        Template=email_templates.EMAIL_CHANGE_TEMPLATE_NAME,
        TemplateData=json.dumps(data),
    )

    return message["MessageId"], data


def send_mail_to_reset_password(ses, username, temp_password):
    images_base_url = get_images_base_url()

    data = {
        **generate_common_data(),
        "USER_ACCOUNT": username,
        "RESET_PASSWORD_URL": app_settings.frontend_url
        + "/create-password?key="
        + quote(temp_password)
        + "&email="
        + quote(username),
        "RESET_PASSWORD_IMAGE": images_base_url + "/ResetPassword.png",
    }

    ses.send_templated_email(
        Source=app_settings.email_sender_address,
        Destination={"ToAddresses": [username]},
        Template=email_templates.RESET_PASSWORD_TEMPLATE_NAME,
        TemplateData=json.dumps(data),
    )


def send_invitation_email(ses, uuid, email, borrower_name, buyer_name, tender_title):
    images_base_url = get_images_base_url()

    data = {
        **generate_common_data(),
        "AWARD_SUPPLIER_NAME": borrower_name,
        "TENDER_TITLE": tender_title,
        "BUYER_NAME": buyer_name,
        "FIND_OUT_MORE_IMAGE_LINK": images_base_url + "/findoutmore.png",
        "REMOVE_ME_IMAGE_LINK": images_base_url + "/removeme.png",
        "FIND_OUT_MORE_URL": app_settings.frontend_url
        + "/application/"
        + quote(uuid)
        + "/intro",
        "REMOVE_ME_URL": app_settings.frontend_url
        + "/application/"
        + quote(uuid)
        + "/decline",
    }

    response = ses.send_templated_email(
        Source=app_settings.email_sender_address,
        Destination={"ToAddresses": [email]},
        Template=email_templates.ACCESS_TO_CREDIT_SCHEME_FOR_MSMES_TEMPLATE_NAME,
        TemplateData=json.dumps(data),
    )

    return response.get("MessageId")


def send_notification_new_app_to_fi(ses, lender_email_group):
    # todo refactor required when this function receives the user language
    images_base_url = get_images_base_url()

    data = {
        **generate_common_data(),
        "LOGIN_URL": app_settings.frontend_url + "/login",
        "LOGIN_IMAGE_LINK": images_base_url + "/logincompleteimage.png",
    }

    ses.send_templated_email(
        Source=app_settings.email_sender_address,
        Destination={"ToAddresses": [lender_email_group]},
        Template=email_templates.NEW_APPLICATION_SUBMISSION_FI_TEMPLATE_NAME,
        TemplateData=json.dumps(data),
    )


def send_notification_new_app_to_ocp(ses, ocp_email_group, lender_name):
    # todo refactor required when this function receives the user language
    images_base_url = get_images_base_url()

    data = {
        **generate_common_data(),
        "F1": lender_name,
        "LOGIN_URL": app_settings.frontend_url + "/login",
        "LOGIN_IMAGE_LINK": images_base_url + "/logincompleteimage.png",
    }

    ses.send_templated_email(
        Source=app_settings.email_sender_address,
        Destination={"ToAddresses": [ocp_email_group]},
        Template=email_templates.NEW_APPLICATION_SUBMISSION_OCP_TEMPLATE_NAME,
        TemplateData=json.dumps(data),
    )


def send_mail_request_to_sme(ses, uuid, lender_name, email_message, sme_email):
    # todo refactor required when this function receives the user language
    images_base_url = get_images_base_url()

    data = {
        **generate_common_data(),
        "FI": lender_name,
        "FI_MESSAGE": email_message,
        "LOGIN_DOCUMENTS_URL": app_settings.frontend_url
        + "/application/"
        + quote(uuid)
        + "/documents",
        "LOGIN_IMAGE_LINK": images_base_url + "/uploadDocument.png",
    }

    response = ses.send_templated_email(
        Source=app_settings.email_sender_address,
        # replace with sme_email on production
        Destination={"ToAddresses": [app_settings.test_mail_receiver]},
        Template=email_templates.REQUEST_SME_DATA_TEMPLATE_NAME,
        TemplateData=json.dumps(data),
    )
    return response.get("MessageId")
