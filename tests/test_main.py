import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.settings import app_settings


def test_info_endpoint():
    client = TestClient(app)
    response = client.get("/info")
    assert response.status_code == 200
    assert response.json() == {
        "Title": "Credere backend",
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
