import os

from dotenv import dotenv_values
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

CONTRACTS_URL = "https://www.datos.gov.co/resource/jbjy-vk9h.json"
AWARDS_URL = "https://www.datos.gov.co/resource/p6dx-8zbt.json"
BORROWER_EMAIL_URL = "https://www.datos.gov.co/resource/vzyx-b5wf.json"
BORROWER_URL = "https://www.datos.gov.co/resource/4ex9-j3n8.json"

pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"

config_env = {
    **dotenv_values(".env"),
    **os.environ,
}  # config are loading separately from main app in order to avoid package dependencies

secop_app_token: str = config_env.get("SECOP_APP_TOKEN", None)
hash_key: str = config_env.get("HASH_KEY", None)
headers = {"X-App-Token": secop_app_token}
