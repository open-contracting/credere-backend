import base64
import hashlib
import hmac
import logging
import re
import uuid

import httpx

from app.core.settings import app_settings

logger = logging.getLogger(__name__)

pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"


def is_valid_email(email: str) -> bool:
    """
    Check if the given email is valid.

    :param email: The email address to validate.
    :type email: str

    :return: True if the email is valid, False otherwise.
    :rtype: bool
    """
    email = email.strip()
    if email and re.search(pattern, email):
        return True
    return False


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
    return base64.b64encode(
        hmac.new(key, message, digestmod=hashlib.sha256).digest()
    ).decode()


def make_request_with_retry(url, headers):
    """
    Make an HTTP request with retry functionality.

    :param url: The URL to make the request to.
    :type url: str
    :param headers: The headers to include in the request.
    :type headers: dict

    :return: The HTTP response from the request if successful, otherwise None.
    :rtype: httpx.Response or None
    """

    transport = httpx.HTTPTransport(retries=3, verify=False)
    client = httpx.Client(transport=transport, timeout=60, headers=headers)

    try:
        response = client.get(url)
        response.raise_for_status()
        return response
    except (httpx.TimeoutException, httpx.HTTPStatusError) as error:
        logger.exception(f"Request failed: {error}")
        return None
    finally:
        client.close()
