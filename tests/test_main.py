import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.settings import app_settings
from app.main import app


def test_info_endpoint():
    client = TestClient(app)
    response = client.get("/info")
    assert response.status_code == 200
    assert response.json() == {
        "Title": "Credence backend",
        "version": app_settings.version,
    }


@pytest.mark.parametrize(
    "url_string",
    [
        app_settings.frontend_url,
    ],
)
def test_valid_frontend_url(url_string):
    url = httpx.URL(url_string)

    assert url.scheme and url.host
