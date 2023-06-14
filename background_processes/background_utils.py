import base64
import hashlib
import hmac
import logging
import uuid

import httpx
import sentry_sdk

from app.db.session import app_settings

from .background_config import headers


def raise_sentry_error(message: str, payload: dict):
    sentry_sdk.capture_exception(message, payload)
    raise ValueError(message)


def generate_uuid(string: str) -> str:
    generated_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, string)
    return str(generated_uuid)


def get_secret_hash(nit_entidad: str) -> str:
    key = app_settings.hash_key
    message = bytes(nit_entidad, "utf-8")
    key = bytes(key, "utf-8")
    return base64.b64encode(
        hmac.new(key, message, digestmod=hashlib.sha256).digest()
    ).decode()


def make_request_with_retry(url):
    transport = httpx.HTTPTransport(retries=3, verify=False)
    client = httpx.Client(transport=transport, timeout=60, headers=headers)

    try:
        response = client.get(url)
        response.raise_for_status()
        return response
    except (httpx.TimeoutException, httpx.HTTPStatusError) as error:
        logging.error(f"Request failed: {error}")
        return None
    finally:
        client.close()


def get_missing_data_keys(input_dict):
    result_dict = {}
    for key, value in input_dict.items():
        if value == "" or value is None:
            result_dict[key] = True
        else:
            result_dict[key] = False

    return result_dict
