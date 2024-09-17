import gettext
from pathlib import Path
from typing import Any

from app.settings import app_settings

localedir = Path(__file__).absolute().parent.parent / "locale"

translators = {
    path.name: gettext.translation("messages", localedir, languages=[path.name])
    for path in localedir.iterdir()
    if path.is_dir()
}


def _(message: str, language: str | None = None, **kwargs: Any) -> str:
    translator = translators.get(language or app_settings.email_template_lang, gettext.NullTranslations())
    return translator.gettext(message) % kwargs


def i(message: str) -> str:
    """Use this identity function to extract messages only."""
    return message
