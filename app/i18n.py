from typing import Any

from app.settings import app_settings

if app_settings.transifex_token and app_settings.transifex_secret:
    # https://developers.transifex.com/docs/python-sdk#initialization
    from transifex.native import init, tx

    init(app_settings.transifex_token, ["es", "en"], app_settings.transifex_secret)
    tx.fetch_translations()


def get_translated_string(key: str, lang: str, params: dict[str, Any] | None = None) -> str:
    from transifex.native import tx

    return tx.translate(key, lang, params=params)
