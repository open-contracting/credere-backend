import pytest

from app.i18n import _
from app.settings import app_settings


@pytest.mark.parametrize(("language", "expected"), [("es", "Pendiente"), ("en", "PENDING")])
def test_translate_implicit(language, expected):
    app_settings.email_template_lang = language

    assert _("PENDING") == expected


@pytest.mark.parametrize(("language", "expected"), [("es", "Pendiente"), ("en", "PENDING")])
def test_translate_explicit(language, expected):
    assert _("PENDING", language) == expected
