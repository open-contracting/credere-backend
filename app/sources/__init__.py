import logging
import re

import httpx

logger = logging.getLogger(__name__)

VALID_EMAIL = r"^[\w\.-]+@[\w\.-]+\.\w+$"


def is_valid_email(email: str) -> bool:
    """
    Check if the given email is valid.

    :param email: The email address to validate.
    :return: True if the email is valid, False otherwise.
    """
    return bool(re.search(VALID_EMAIL, email))


def make_request_with_retry(url: str, headers: dict[str, str]) -> httpx.Response:
    """
    Make an HTTP request with retry functionality.

    :param url: The URL to make the request to.
    :param headers: The headers to include in the request.
    :return: The HTTP response from the request if successful, otherwise None.
    """

    transport = httpx.HTTPTransport(retries=3, verify=False)
    client = httpx.Client(transport=transport, timeout=60, headers=headers)

    try:
        response = client.get(url)
        response.raise_for_status()
        return response
    finally:
        client.close()
