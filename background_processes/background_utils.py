import base64
import hashlib
import hmac
import json
import uuid
from urllib.parse import quote

import boto3

from ..app.core.settings import app_settings
from ..app.email_templates import email_templates
from .background_config import hash_key

# cognito = boto3.client(
#     "cognito-idp",
#     region_name=app_settings.aws_region,
#     aws_access_key_id=app_settings.aws_access_key,
#     aws_secret_access_key=app_settings.aws_client_secret,
# )

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


def send_invitation_email(uuid):
    data = {
        **generate_common_data(),
        "AWARD_SUPPLIER_NAME": "PROVEEDOR XX",
        "TENDER_TITLE": "PROVISION_DE_COMIDA",
        "BUYER_NAME": "INSTITUCION PUBLICA XX",
        "FIND_OUT_MORE_IMAGE_LINK": "https://adrian-personal.s3.sa-east-1.amazonaws.com/findoutmore.png",
        "REMOVE_ME_IMAGE_LINK": "https://adrian-personal.s3.sa-east-1.amazonaws.com/removeme.png",
        "FIND_OUT_MORE_URL": app_settings.frontend_url
        + "/application/"
        + quote(uuid)
        + "/intro",
        "REMOVE_ME_URL": app_settings.frontend_url
        + "/application/"
        + quote(uuid)
        + "/decline",
    }

    sesClient.send_templated_email(
        Source=app_settings.email_sender_address,
        Destination={"ToAddresses": app_settings.test_mail_receiver},
        Template=email_templates.ACCESS_TO_CREDIT_SCHEME_FOR_MSMES_TEMPLATE_NAME,
        TemplateData=json.dumps(data),
    )


def get_secret_hash(nit_entidad: str) -> str:
    key = hash_key
    message = bytes(nit_entidad, "utf-8")
    key = bytes(key, "utf-8")
    return base64.b64encode(
        hmac.new(key, message, digestmod=hashlib.sha256).digest()
    ).decode()
