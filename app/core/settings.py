import os

from dotenv import dotenv_values
from pydantic import BaseSettings

VERSION: str = "0.1.1"


def merge_dicts_with_condition(main_dict, override_dict):
    temp_dict = {**override_dict}
    filtered_dict = {key: value for key, value in temp_dict.items() if value != ""}
    merged_dict = {**main_dict, **filtered_dict}
    return merged_dict


# load local file development variables
# override loaded values with system environment variables if not empty ''
config_env = merge_dicts_with_condition(dotenv_values(".env"), os.environ)


class Settings(BaseSettings):
    app_name: str = "Credere API"
    version: str = config_env.get("VERSION", VERSION)
    aws_region: str = config_env.get("AWS_REGION", "us-west-2")
    cognito_pool_id: str = config_env.get("COGNITO_POOL_ID", None)
    aws_access_key: str = config_env.get("AWS_ACCESS_KEY", None)
    aws_client_secret: str = config_env.get("AWS_CLIENT_SECRET", None)
    email_sender_address: str = config_env.get(
        "EMAIL_SENDER_ADDRESS", "credere@noreply.open-contracting.org"
    )
    cognito_client_id: str = config_env.get("COGNITO_CLIENT_ID", None)
    cognito_client_secret: str = config_env.get("COGNITO_CLIENT_SECRET", None)
    database_url: str = config_env.get("DATABASE_URL", None)
    frontend_url: str = config_env.get("FRONTEND_URL", "http://localhost:3000")
    sentry_dsn: str = config_env.get("SENTRY_DNS", None)
    images_base_url: str = config_env.get(
        "IMAGES_BASE_URL", "http://ocp22.open-contracting.org/images"
    )
    images_lang_subpath: str = config_env.get("IMAGES_LANG_SUBPATH", "")
    facebook_link: str = config_env.get("FACEBOOK_LINK", "www.facebook.com")
    twitter_link: str = config_env.get("TWITTER_LINK", "www.twitter.com")
    link_link: str = config_env.get("LINK_LINK", "http://localhost:3000")
    test_mail_receiver: str = config_env.get("TEST_MAIL_RECEIVER", None)
    colombia_secop_app_token: str = config_env.get("COLOMBIA_SECOP_APP_TOKEN", None)
    hash_key: str = config_env.get("HASH_KEY", None)
    application_expiration_days: int = config_env.get("APPLICATION_EXPIRATION_DAYS", 7)
    secop_pagination_limit: int = config_env.get("SECOP_PAGINATION_LIMIT", 5)
    secop_default_days_from_ultima_actualizacion: int = config_env.get(
        "SECOP_DEFAULT_DAYS_FROM_ULTIMA_ACTUALIZACION", 365
    )
    reminder_days_before_expiration: int = config_env.get(
        "REMINDER_DAYS_BEFORE_EXPIRATION", 3
    )

    class Config:
        env_file = ".env"


app_settings = Settings()
