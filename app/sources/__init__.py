import httpx

# The reasons for this configuration were not documented in 427ce63. Assume server and certificate instability.
client = httpx.Client(transport=httpx.HTTPTransport(retries=3, verify=False), timeout=60)


def make_request_with_retry(url: str, headers: dict[str, str]) -> httpx.Response:
    """
    Make an HTTP request with retry functionality.

    :param url: The URL to make the request to.
    :param headers: The headers to include in the request.
    :return: The HTTP response from the request if successful, otherwise None.
    """
    response = client.get(url, headers=headers)
    response.raise_for_status()
    return response
