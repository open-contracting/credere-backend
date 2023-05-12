from fastapi.testclient import TestClient
from app.main import app
from app.core.settings import Settings

settings = Settings()


def test_info_endpoint():
    client = TestClient(app)
    response = client.get("/info")
    assert response.status_code == 200
    assert response.json() == {"Title": "Credence backend", "version": settings.version}
