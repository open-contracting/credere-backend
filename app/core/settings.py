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

    class Config:
        env_file = ".env"


app_settings = Settings()
