import base64
import hashlib
import hmac
import uuid

import background_config


def generate_uuid(string: str) -> str:
    generated_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, string)
    return str(generated_uuid)


def get_secret_hash(nit_entidad: str) -> str:
    key = background_config.hash_key
    message = bytes(nit_entidad, "utf-8")
    key = bytes(key, "utf-8")
    return base64.b64encode(
        hmac.new(key, message, digestmod=hashlib.sha256).digest()
    ).decode()
