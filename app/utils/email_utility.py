import json
from urllib.parse import quote

from app.email_templates import NEW_USER_TEMPLATE_NAME

from ..core.settings import app_settings


def generate_common_data():
    return {
        "LINK-TO-WEB-VERSION": "www.google.com",
        "OCP_LOGO": app_settings.temporal_bucket + "/logoocp.jpg",
        "TWITTER_LOGO": app_settings.temporal_bucket + "/twiterlogo.png",
        "FB_LOGO": app_settings.temporal_bucket + "/facebook.png",
        "LINK_LOGO": app_settings.temporal_bucket + "/link.png",
        "TWITTER_LINK": "www.google.com",
        "FACEBOOK_LINK": "www.google.com",
        "LINK_LINK": "www.google.com",
    }


def send_mail_to_new_user(ses, name, username, temp_password):
    data = {
        **generate_common_data(),
        "USER": name,
        "SET_PASSWORD_IMAGE_LINK": app_settings.temporal_bucket + "/set_password.png",
        "LOGIN_URL": app_settings.frontend_url
        + "/create-password?key="
        + quote(temp_password)
        + "&email="
        + quote(username),
    }

    ses.send_templated_email(
        Source=app_settings.email_sender_address,
        Destination={"ToAddresses": [username]},
        Template=NEW_USER_TEMPLATE_NAME,
        TemplateData=json.dumps(data),
    )


def send_mail_to_reset_password(ses, username, temp_password):
    data = {
        **generate_common_data(),
        "USER": "test user",
        "USER_ACCOUNT": username,
        "RESET_PASSWORD_URL": app_settings.frontend_url
        + "/create-password?key="
        + quote(temp_password)
        + "&email="
        + quote(username),
        "RESET_PASSWORD_IMAGE": app_settings.temporal_bucket + "/ResetPassword.png",
    }

    ses.send_templated_email(
        Source=app_settings.email_sender_address,
        Destination={"ToAddresses": [username]},
        Template="credere-ResetPassword",
        TemplateData=json.dumps(data),
    )
