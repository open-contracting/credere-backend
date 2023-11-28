from typing import Any

from app.settings import app_settings

if app_settings.transifex_token and app_settings.transifex_secret:
    from transifex.native import init, tx

    # if more langs added to project add them here
    init(app_settings.transifex_token, ["es", "en"], app_settings.transifex_secret)
    # populate toolkit memory cache with translations from CDS service the first time
    tx.fetch_translations()


def get_translated_string(key: str, lang: str, params: dict[str, Any] | None = None) -> str:
    from transifex.native import tx

    return tx.translate(key, lang, params=params)
