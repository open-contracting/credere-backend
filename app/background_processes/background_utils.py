import logging
import re

import httpx

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
