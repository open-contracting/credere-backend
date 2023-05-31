import os

from dotenv import dotenv_values
from pydantic import BaseSettings

VERSION: str = "0.1.0"


config_env = {
    **dotenv_values(".env"),  # load local file development variables
    **os.environ,  # override loaded values with system environment variables
}


class Settings(BaseSettings):
    app_name: str = "Credere API"
    DB_URL: str = config_env.get("DB_URL", "sqlite:///./test_db.db")

    class Config:
        env_file = ".env"


settings = Settings()
