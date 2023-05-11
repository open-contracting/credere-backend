import os
from dotenv import dotenv_values

from pydantic import BaseSettings

config_env = {
    **dotenv_values(".env"),  # load local file development variables
    **os.environ,  # override loaded values with system environment variables
}


class Settings(BaseSettings):
    app_name: str = "Credere API"
    version: str = config_env["VERSION"]

    class Config:
        env_file = ".env"
