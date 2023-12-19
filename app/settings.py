import logging.config
import re
from typing import Any

import sentry_sdk
from pydantic_settings import BaseSettings, SettingsConfigDict

VERSION: str = "0.1.1"


def sentry_filter_transactions(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """
    Filter transactions to be sent to Sentry.
    This function prevents transactions that interact with AWS Cognito from being sent to Sentry.

    :param event: The event data.
    :param hint: A dictionary of extra data passed to the function.
    :return: The event data if it should be sent to Sentry, otherwise None.
    """
    data_url = event["breadcrumbs"]["values"][0]["data"]["url"] or None
    if data_url and re.search(r"https://cognito-idp.*\.amazonaws\.com", data_url):
        return None
    return event


class Settings(BaseSettings):
    # https://docs.pydantic.dev/latest/concepts/pydantic_settings/#usage
    # By default, the environment variable name is the same as the field name.
    app_name: str = "Credere API"
    version: str = VERSION
    log_level: int | str = logging.INFO
    aws_region: str = "us-west-2"
    cognito_pool_id: str = ""
    aws_access_key: str = ""
    aws_client_secret: str = ""
    email_sender_address: str = "credere@noreply.open-contracting.org"
    cognito_client_id: str = ""
    cognito_client_secret: str = ""
    database_url: str = ""
    test_database_url: str = ""
    frontend_url: str = "http://localhost:3000"
    sentry_dsn: str = ""
    images_base_url: str = "https://credere.open-contracting.org/images"
    email_template_lang: str = "es"
    facebook_link: str = "www.facebook.com"
    twitter_link: str = "www.twitter.com"
    link_link: str = "http://localhost:3000"
    test_mail_receiver: str = "credere@noreply.open-contracting.org"
    colombia_secop_app_token: str = ""
    hash_key: str = ""
    application_expiration_days: int = 7
    secop_pagination_limit: int = 5
    secop_default_days_from_ultima_actualizacion: int = 365
    days_to_erase_borrowers_data: int = 7
    days_to_change_to_lapsed: int = 14
    ocp_email_group: str = "credere@noreply.open-contracting.org"
    max_file_size_mb: int = 5
    reminder_days_before_expiration: int = 3
    progress_to_remind_started_applications: float = 0.7
    environment: str = "development"
    transifex_token: str = ""
    transifex_secret: str = ""
    model_config = SettingsConfigDict(env_file=".env")


app_settings = Settings()

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "console": {
                "format": "%(asctime)s %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
            },
        },
        "loggers": {
            "": {
                "handlers": ["console"],
                "level": app_settings.log_level,
            },
        },
    }
)

if app_settings.sentry_dsn:
    sentry_sdk.init(
        dsn=app_settings.sentry_dsn,
        before_send=sentry_filter_transactions,
        # Set traces_sample_rate to 1.0 to capture 100% of transactions for performance monitoring.
        traces_sample_rate=1.0,
    )

# email template names
NEW_USER_TEMPLATE_NAME = "credere-NewAccountCreated"
RESET_PASSWORD_TEMPLATE_NAME = "credere-ResetPassword"
ACCESS_TO_CREDIT_SCHEME_FOR_MSMES_TEMPLATE_NAME = "credere-AccessToCreditSchemeForMSMEs"
INTRO_REMINDER_TEMPLATE_NAME = "credere-AccessToCreditSchemeReminder"
APPLICATION_REMINDER_TEMPLATE_NAME = "credere-ApplicationReminder"
