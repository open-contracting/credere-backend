import base64
import hashlib
import hmac
import uuid
from enum import Enum

from fastapi import HTTPException, status

from app.settings import app_settings


class ERROR_CODES(Enum):
    BORROWER_FIELD_VERIFICATION_MISSING = "BORROWER_FIELD_VERIFICATION_MISSING"
    DOCUMENT_VERIFICATION_MISSING = "DOCUMENT_VERIFICATION_MISSING"
    APPLICATION_LAPSED = "APPLICATION_LAPSED"
    APPLICATION_ALREADY_COPIED = "APPLICATION_ALREADY_COPIED"


def get_object_or_404(session, model, field, value):
    obj = model.first_by(session, field, value)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{model.__name__} not found")
    return obj


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
