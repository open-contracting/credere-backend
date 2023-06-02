import base64
import hashlib
import hmac

import background_config


def get_secret_hash(nit_entidad: str):
    key = background_config.hash_key
    message = bytes(nit_entidad, "utf-8")
    key = bytes(key, "utf-8")
    return base64.b64encode(
        hmac.new(key, message, digestmod=hashlib.sha256).digest()
    ).decode()
