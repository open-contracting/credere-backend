from fastapi.testclient import TestClient
from app.main import app
from app.schema.user_tables.users import User

user = User(
    type="customer",
    email="jane@example.com",
    external_id="12345",
    fl_id=10,
)


def test_read_user():
    client = TestClient(app)
    response = client.get("/users/")

    assert response.status_code == 200
