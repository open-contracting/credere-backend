import logging

import httpx
from email_validator import EmailSyntaxError, EmailUndeliverableError, validate_email

logger = logging.getLogger(__name__)


def is_valid_email(email: str) -> bool:
    """
    Check if the given email is valid.

    :param email: The email address to validate.
    :return: True if the email is valid, False otherwise.
    """
    try:
        return bool(validate_email(email, allow_smtputf8=False))
    except (EmailSyntaxError, EmailUndeliverableError):
        return False


def make_request_with_retry(url: str, headers: dict[str, str]) -> httpx.Response:
    """
    Make an HTTP request with retry functionality.

    :param url: The URL to make the request to.
    :param headers: The headers to include in the request.
    :return: The HTTP response from the request if successful, otherwise None.
    """

    transport = httpx.HTTPTransport(retries=3, verify=False)
    client = httpx.Client(transport=transport, timeout=60, headers=headers, params={})

    try:
        response = client.get(url, params={})
        response.raise_for_status()
        return response
    finally:
        client.close()
