import os
from functools import lru_cache

from dotenv import dotenv_values
from pydantic import BaseSettings

VERSION: str = "0.1.0"


config_env = {
    **dotenv_values(".env"),  # load local file development variables
    **os.environ,  # override loaded values with system environment variables
}


@lru_cache()
class Settings(BaseSettings):
    app_name: str = "Credere API"
    version: str = config_env.get("VERSION", "0.1.1")
    cognito_aws_region: str = config_env.get("COGNITO_AWS_REGION", None)
    cognito_pool_id: str = config_env.get("COGNITO_POOL_ID", None)
    cognito_client_id: str = config_env.get("COGNITO_CLIENT_ID", None)
    cognito_secret_key: str = config_env.get("COGNITO_SECRET_KEY", None)
    access_key: str = config_env.get("ACCESS_KEY", None)
    client_secret: str = config_env.get("CLIENT_SECRET", None)


    class Config:
        env_file = ".env"
