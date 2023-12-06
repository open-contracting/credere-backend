import logging
import logging.config
import os
import re
from typing import Any

import sentry_sdk
from dotenv import dotenv_values
from pydantic_settings import BaseSettings, SettingsConfigDict

VERSION: str = "0.1.1"


def merge_dicts_with_condition(main_dict: dict[str, Any], override_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Merges two dictionaries with the condition that empty strings ('') from the override_dict are not included in the
    merged dictionary. If a key in the main_dict has a corresponding non-empty string value in override_dict,
    the value from override_dict will replace the value from main_dict in the resulting merged dictionary.

    :param main_dict: The main dictionary, which serves as the base dictionary for the merge operation.
    :param override_dict: The dictionary that is used to update the main_dict.
                          If a key-value pair in override_dict has a non-empty string value,
                          it will replace the corresponding key-value pair in main_dict.
    :return: The merged dictionary.
    """
    temp_dict = {**override_dict}
    filtered_dict = {key: value for key, value in temp_dict.items() if value != ""}
    return {**main_dict, **filtered_dict}


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


# load local file development variables
# override loaded values with system environment variables if not empty ''
config_env = merge_dicts_with_condition(dotenv_values(".env"), os.environ)


class Settings(BaseSettings):
    app_name: str = "Credere API"
    version: str = config_env.get("VERSION", VERSION)
    log_level: int | str = config_env.get("LOG_LEVEL", logging.INFO)
    aws_region: str = config_env.get("AWS_REGION", "us-west-2")
    cognito_pool_id: str = config_env.get("COGNITO_POOL_ID", "")
    aws_access_key: str = config_env.get("AWS_ACCESS_KEY", "")
    aws_client_secret: str = config_env.get("AWS_CLIENT_SECRET", "")
    email_sender_address: str = config_env.get("EMAIL_SENDER_ADDRESS", "credere@noreply.open-contracting.org")
    cognito_client_id: str = config_env.get("COGNITO_CLIENT_ID", "")
    cognito_client_secret: str = config_env.get("COGNITO_CLIENT_SECRET", "")
    database_url: str = config_env.get("DATABASE_URL", "")
    test_database_url: str = config_env.get("TEST_DATABASE_URL", "")
    frontend_url: str = config_env.get("FRONTEND_URL", "http://localhost:3000")
    sentry_dsn: str = config_env.get("SENTRY_DSN", "")
    images_base_url: str = config_env.get("IMAGES_BASE_URL", "https://credere.open-contracting.org/images")
    email_template_lang: str = config_env.get("EMAIL_TEMPLATE_LANG", "es")
    facebook_link: str = config_env.get("FACEBOOK_LINK", "www.facebook.com")
    twitter_link: str = config_env.get("TWITTER_LINK", "www.twitter.com")
    link_link: str = config_env.get("LINK_LINK", "http://localhost:3000")
    test_mail_receiver: str = config_env.get("TEST_MAIL_RECEIVER", "credere@noreply.open-contracting.org")
    colombia_secop_app_token: str = config_env.get("COLOMBIA_SECOP_APP_TOKEN", "")
    hash_key: str = config_env.get("HASH_KEY", "")
    application_expiration_days: int = config_env.get("APPLICATION_EXPIRATION_DAYS", 7)
    secop_pagination_limit: int = config_env.get("SECOP_PAGINATION_LIMIT", 5)
    secop_default_days_from_ultima_actualizacion: int = config_env.get(
        "SECOP_DEFAULT_DAYS_FROM_ULTIMA_ACTUALIZACION", 365
    )
    days_to_erase_borrower_data: int = config_env.get("DAYS_TO_ERASE_BORROWERS_DATA", 7)
    days_to_change_to_lapsed: int = config_env.get("DAYS_TO_CHANGE_TO_LAPSED", 14)
    ocp_email_group: str = config_env.get("OCP_EMAIL_GROUP", "credere@noreply.open-contracting.org")
    max_file_size_mb: int = config_env.get("MAX_FILE_SIZE_MB", 5)
    reminder_days_before_expiration: int = config_env.get("REMINDER_DAYS_BEFORE_EXPIRATION", 3)
    progress_to_remind_started_applications: float = config_env.get("PROGRESS_TO_REMIND_STARTED_APPLICATIONS", 0.7)
    environment: str = config_env.get("ENVIRONMENT", "development")
    transifex_token: str = config_env.get("TRANSIFEX_TOKEN", "")
    transifex_secret: str = config_env.get("TRANSIFEX_SECRET", "")
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
