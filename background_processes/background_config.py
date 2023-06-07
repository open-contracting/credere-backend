import os

from dotenv import dotenv_values

URLS = {
    "CONTRACTS": "https://www.datos.gov.co/resource/jbjy-vk9h.json",
    "AWARDS": "https://www.datos.gov.co/resource/p6dx-8zbt.json",
    "BORROWER_EMAIL": "https://www.datos.gov.co/resource/vzyx-b5wf.json",
    "BORROWER": "https://www.datos.gov.co/resource/4ex9-j3n8.json?&es_pyme=SI",
}

pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"

config_env = {
    **dotenv_values(".env"),
    **os.environ,
}  # config are loading separately from main app in order to avoid package dependencies

colombia_secop_app_token: str = config_env.get("COLOMBIA_SECOP_APP_TOKEN", None)
hash_key: str = config_env.get("HASH_KEY", None)
secop_pagination_limit: str = config_env.get("SECOP_PAGINATION_LIMIT", None)
headers = {"X-App-Token": colombia_secop_app_token}
