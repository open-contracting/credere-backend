from fastapi.testclient import TestClient

from app.core.settings import Settings
from app.main import app

settings = Settings()


def test_info_endpoint():
    client = TestClient(app)
    response = client.get("/info")
    assert response.status_code == 200
    assert response.json() == {"Title": "Credence backend", "version": settings.version}
