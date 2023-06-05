import base64
import hashlib
import hmac
import uuid

from .background_config import hash_key


def generate_uuid(string: str) -> str:
    generated_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, string)
    return str(generated_uuid)


def send_invitation_email(url, email):
    return f"sends {url} to {email}"


def get_secret_hash(nit_entidad: str) -> str:
    key = hash_key
    message = bytes(nit_entidad, "utf-8")
    key = bytes(key, "utf-8")
    return base64.b64encode(
        hmac.new(key, message, digestmod=hashlib.sha256).digest()
    ).decode()
