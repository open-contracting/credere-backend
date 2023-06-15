import os

from dotenv import dotenv_values
from pydantic import BaseSettings

VERSION: str = "0.1.1"

config_env = {
    **dotenv_values(".env"),  # load local file development variables
    **os.environ,  # override loaded values with system environment variables
}


class Settings(BaseSettings):
    app_name: str = "Credere API"
    db_url: str = config_env.get("DB_URL", "sqlite:///./test_db.db")
    version: str = config_env.get("VERSION", VERSION)
    aws_region: str = config_env.get("AWS_REGION", "us-west-2")
    cognito_pool_id: str = config_env.get("COGNITO_POOL_ID", None)
    aws_access_key: str = config_env.get("AWS_ACCESS_KEY", None)
    aws_client_secret: str = config_env.get("AWS_CLIENT_SECRETAWS_CLIENT_SECRET", None)
    email_sender_address: str = config_env.get(
        "EMAIL_SENDER_ADDRESS", "credere@noreply.open-contracting.org"
    )
    cognito_client_id: str = config_env.get("COGNITO_CLIENT_ID", None)
    cognito_client_secret: str = config_env.get("COGNITO_CLIENT_SECRET", None)
    database_url: str = config_env.get("DATABASE_URL", None)
    frontend_url: str = config_env.get("FRONTEND_URL", "http://localhost:3000")
    sentry_dsn: str = config_env.get("SENTRY_DNS", None)
    temporal_bucket: str = config_env.get(
        "TEMPORAL_BUCKET", "https://adrian-personal.s3.sa-east-1.amazonaws.com"
    )
    front_public_images_es: str = config_env.get(
        "FRONT_PUBLIC_IMAGES_ES", "/public/images/es"
    )
    front_public_images_en: str = config_env.get(
        "FRONT_PUBLIC_IMAGES_EN", "/public/images/es"
    )
    facebook_link: str = config_env.get("FACEBOOK_LINK", "www.facebook.com")
    twitter_link: str = config_env.get("TWITTER_LINK", "www.twitter.com")
    link_link: str = config_env.get("LINK_LINK", "http://localhost:3000")
    test_mail_receiver: str = config_env.get("TEST_MAIL_RECEIVER", "aomm24@gmail.com")
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
