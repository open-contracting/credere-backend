from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app
from app.schema.user_tables.users import ApplicationAction, User

test_time = datetime.now()

application_action = ApplicationAction(
    type="action_type",
    data={"key1": "value1", "key2": "value2"},
    application_id="application_id_value",
    user_id=123,
    created_at=test_time,
)

user = User(
    id=1,
    type="customer",
    email="jane@example.com",
    external_id="12345",
    fl_id=10,
)


def test_read_user():
    client = TestClient(app)
    response = client.get("/users/")

    response_json = response.json()
    assert response.status_code == 200
    assert response_json["id"] == user.id
    assert response_json["type"] == user.type
    assert response_json["email"] == user.email
    assert response_json["external_id"] == user.external_id
    assert response_json["fl_id"] == user.fl_id
