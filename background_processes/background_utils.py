import base64
import hashlib
import hmac

from .background_config import hash_key


def get_secret_hash(nit_entidad: str):
    key = hash_key
    message = bytes(nit_entidad, "utf-8")
    key = bytes(key, "utf-8")
    return base64.b64encode(
        hmac.new(key, message, digestmod=hashlib.sha256).digest()
    ).decode()
