from app.db.session import app_settings

URLS = {
    "CONTRACTS": "https://www.datos.gov.co/resource/jbjy-vk9h.json",
    "AWARDS": "https://www.datos.gov.co/resource/p6dx-8zbt.json",
    "BORROWER_EMAIL": "https://www.datos.gov.co/resource/vzyx-b5wf.json",
    "BORROWER": "https://www.datos.gov.co/resource/4ex9-j3n8.json?&es_pyme=SI",
}

pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"


headers = {"X-App-Token": app_settings.colombia_secop_app_token}
