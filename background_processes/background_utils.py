import base64
import hashlib
import hmac
import uuid

import boto3

from ..app.core.settings import app_settings
from .background_config import hash_key

cognito = boto3.client(
    "cognito-idp",
    region_name=app_settings.aws_region,
    aws_access_key_id=app_settings.aws_access_key,
    aws_secret_access_key=app_settings.aws_client_secret,
)

sesClient = boto3.client(
    "ses",
    region_name=app_settings.aws_region,
    aws_access_key_id=app_settings.aws_access_key,
    aws_secret_access_key=app_settings.aws_client_secret,
)


def generate_uuid(string: str) -> str:
    generated_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, string)
    return str(generated_uuid)


def generate_common_data():
    return {
        "LINK-TO-WEB-VERSION": app_settings.frontend_url,
        "OCP_LOGO": app_settings.temporal_bucket + "/logoocp.jpg",
        "TWITTER_LOGO": app_settings.temporal_bucket + "/twiterlogo.png",
        "FB_LOGO": app_settings.temporal_bucket + "/facebook.png",
        "LINK_LOGO": app_settings.temporal_bucket + "/link.png",
        "TWITTER_LINK": app_settings.twitter_link,
        "FACEBOOK_LINK": app_settings.facebook_link,
        "LINK_LINK": app_settings.link_link,
    }


def send_invitation_email(url, email):
    # data = {
    #     **generate_common_data(),
    #     # "USER": name,
    #     # "SET_PASSWORD_IMAGE_LINK": app_settings.temporal_bucket + "/set_password.png",
    #     # "LOGIN_URL": app_settings.frontend_url
    #     # + "/create-password?key="
    #     # + quote(temp_password)
    #     # + "&email="
    #     # + quote(username),
    # }

    sesClient.send_templated_email(
        Source=app_settings.email_sender_address,
        # Destination={"ToAddresses": [username]},
        # Template=email_templates.NEW_USER_TEMPLATE_NAME,
        # TemplateData=json.dumps(data),
    )

    # return f"sends {url} to {email}"


def get_secret_hash(nit_entidad: str) -> str:
    key = hash_key
    message = bytes(nit_entidad, "utf-8")
    key = bytes(key, "utf-8")
    return base64.b64encode(
        hmac.new(key, message, digestmod=hashlib.sha256).digest()
    ).decode()
