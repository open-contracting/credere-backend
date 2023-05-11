from fastapi.testclient import TestClient
from app.main import app


def test_info_endpoint():
    client = TestClient(app)
    response = client.get("/info")
    assert response.status_code == 200
    assert response.json() == {"Title": "Credence backend", "version": "0.0.1"}
