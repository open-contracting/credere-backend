import base64
import hashlib
import hmac
import uuid

import sentry_sdk

from app.db.session import app_settings


def raise_sentry_error(message: str, payload: dict):
    sentry_sdk.capture_exception(message, payload)
    raise ValueError(message)


def generate_uuid(string: str) -> str:
    generated_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, string)
    return str(generated_uuid)


def send_invitation_email(url, email, uuid):
    return f"sends {url}/{uuid} to {email}"


def get_secret_hash(nit_entidad: str) -> str:
    key = app_settings.hash_key
    message = bytes(nit_entidad, "utf-8")
    key = bytes(key, "utf-8")
    return base64.b64encode(
        hmac.new(key, message, digestmod=hashlib.sha256).digest()
    ).decode()
