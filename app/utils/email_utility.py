import json
import logging
from urllib.parse import quote

from app.core import settings


def generate_common_data():
    return {
        "LINK-TO-WEB-VERSION": settings.app_settings.frontend_url,
        "OCP_LOGO": settings.app_settings.images_base_url + "/logoocp.jpg",
        "TWITTER_LOGO": settings.app_settings.images_base_url + "/twiterlogo.png",
        "FB_LOGO": settings.app_settings.images_base_url + "/facebook.png",
        "LINK_LOGO": settings.app_settings.images_base_url + "/link.png",
        "TWITTER_LINK": settings.app_settings.twitter_link,
        "FACEBOOK_LINK": settings.app_settings.facebook_link,
        "LINK_LINK": settings.app_settings.link_link,
    }


def get_images_base_url():
    # todo refactor required when this function receives the user language

    images_base_url = settings.app_settings.images_base_url
    if settings.app_settings.images_lang_subpath != "":
        images_base_url = (
            f"{images_base_url}/{settings.app_settings.images_lang_subpath}"
        )

    return images_base_url


def send_mail_to_new_user(ses, name, username, temp_password):
    # todo refactor required when this function receives the user language

    images_base_url = get_images_base_url()

    data = {
        **generate_common_data(),
        "USER": name,
        "SET_PASSWORD_IMAGE_LINK": f"{images_base_url}/set_password.png",
        "LOGIN_URL": settings.app_settings.frontend_url
        + "/create-password?key="
        + quote(temp_password)
        + "&email="
        + quote(username),
    }

    ses.send_templated_email(
        Source=settings.app_settings.email_sender_address,
        Destination={"ToAddresses": [username]},
        Template=settings.NEW_USER_TEMPLATE_NAME,
        TemplateData=json.dumps(data),
    )


def send_mail_to_reset_password(ses, username, temp_password):
    images_base_url = get_images_base_url()

    data = {
        **generate_common_data(),
        "USER_ACCOUNT": username,
        "RESET_PASSWORD_URL": settings.app_settings.frontend_url
        + "/create-password?key="
        + quote(temp_password)
        + "&email="
        + quote(username),
        "RESET_PASSWORD_IMAGE": images_base_url + "/ResetPassword.png",
    }

    ses.send_templated_email(
        Source=settings.app_settings.email_sender_address,
        Destination={"ToAddresses": [username]},
        Template=settings.RESET_PASSWORD_TEMPLATE_NAME,
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
        "FIND_OUT_MORE_URL": settings.app_settings.frontend_url
        + "/application/"
        + quote(uuid)
        + "/intro",
        "REMOVE_ME_URL": settings.app_settings.frontend_url
        + "/application/"
        + quote(uuid)
        + "/decline",
    }

    # change to email in prod
    logging.info(
        f"NON PROD - Email to: {email} sent to {settings.app_settings.test_mail_receiver}"
    )

    response = ses.send_templated_email(
        Source=settings.app_settings.email_sender_address,
        Destination={
            "ToAddresses": [settings.app_settings.test_mail_receiver]
        },  # change to email in prod
        Template=settings.ACCESS_TO_CREDIT_SCHEME_FOR_MSMES_TEMPLATE_NAME,
        TemplateData=json.dumps(data),
    )
    return response.get("MessageId")


def send_mail_intro_reminder(ses, uuid, email, borrower_name, buyer_name, tender_title):
    images_base_url = get_images_base_url()
    data = {
        **generate_common_data(),
        "AWARD_SUPPLIER_NAME": borrower_name,
        "TENDER_TITLE": tender_title,
        "BUYER_NAME": buyer_name,
        "FIND_OUT_MORE_URL": settings.app_settings.frontend_url
        + "/application/"
        + quote(uuid)
        + "/intro",
        "FIND_OUT_MORE_IMAGE_LINK": images_base_url + "/findoutmore.png",
        "REMOVE_ME_IMAGE_LINK": images_base_url + "/removeme.png",
        "REMOVE_ME_URL": settings.app_settings.frontend_url
        + "/application/"
        + quote(uuid)
        + "/decline",
    }
    # change to email in prod
    logging.info(
        f"NON PROD - Email to: {email} sent to {settings.app_settings.test_mail_receiver}"
    )

    response = ses.send_templated_email(
        Source=settings.app_settings.email_sender_address,
        Destination={
            "ToAddresses": [settings.app_settings.test_mail_receiver]
        },  # change to email in prod
        Template=settings.INTRO_REMINDER_TEMPLATE_NAME,
        TemplateData=json.dumps(data),
    )
    message_id = response.get("MessageId")
    logging.info(message_id)
    return response.get("MessageId")


def send_mail_submit_reminder(
    ses, uuid, email, borrower_name, buyer_name, tender_title
):
    images_base_url = get_images_base_url()
    data = {
        **generate_common_data(),
        "AWARD_SUPPLIER_NAME": borrower_name,
        "TENDER_TITLE": tender_title,
        "BUYER_NAME": buyer_name,
        "APPLY_FOR_CREDIT_URL": settings.app_settings.frontend_url
        + "/application/"
        + quote(uuid)
        + "/intro",
        "APPLY_FOR_CREDIT_IMAGE_LINK": images_base_url + "/applyForCredit.png",
        "REMOVE_ME_IMAGE_LINK": images_base_url + "/removeme.png",
        "REMOVE_ME_URL": settings.app_settings.frontend_url
        + "/application/"
        + quote(uuid)
        + "/decline",
    }
    # change to email in prod
    logging.info(
        f"NON PROD - Email to: {email} sent to {settings.app_settings.test_mail_receiver}"
    )

    response = ses.send_templated_email(
        Source=settings.app_settings.email_sender_address,
        Destination={
            "ToAddresses": [settings.app_settings.test_mail_receiver]
        },  # change to email in prod
        Template=settings.APPLICATION_REMINDER_TEMPLATE_NAME,
        TemplateData=json.dumps(data),
    )
    message_id = response.get("MessageId")
    logging.info(message_id)
    return response.get("MessageId")
