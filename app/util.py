import base64
import hashlib
import hmac
import uuid

from app.settings import app_settings


def generate_uuid(string: str) -> str:
    """
    Generate a UUID based on the given string.

    :param string: The input string to generate the UUID from.
    :type string: str

    :return: The generated UUID.
    :rtype: str
    """

    generated_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, string)
    return str(generated_uuid)


def get_secret_hash(nit_entidad: str) -> str:
    """
    Get the secret hash based on the given entity's NIT (National Taxpayer's ID).

    :param nit_entidad: The NIT (National Taxpayer's ID) of the entity.
    :type nit_entidad: str

    :return: The secret hash generated from the NIT.
    :rtype: str
    """

    key = app_settings.hash_key
    message = bytes(nit_entidad, "utf-8")
    key = bytes(key, "utf-8")
    return base64.b64encode(hmac.new(key, message, digestmod=hashlib.sha256).digest()).decode()
