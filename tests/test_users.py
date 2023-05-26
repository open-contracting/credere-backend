import json
from typing import Any, Generator

import boto3
import pytest
from botocore.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from moto import mock_cognitoidp
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import get_db
from app.routers import users
from app.schema.user_tables.users import User

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_db.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def start_application():
    app = FastAPI()
    app.include_router(users.router)
    return app


@pytest.fixture(scope="function")
def app() -> Generator[FastAPI, Any, None]:
    """
    This will create a new test database in order to prevent extra entries
    in the main one
    """
    User.metadata.create_all(engine)  # Create the tables.
    _app = start_application()
    yield _app
    User.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(app: FastAPI) -> Generator[SessionTesting, Any, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionTesting(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(app: FastAPI, db_session: SessionTesting) -> Generator[TestClient, Any, None]:
    def _get_test_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_test_db
    with TestClient(app) as client:
        yield client


def test_create_user(client):
    data = {
        "type": "FI User",
        "language": "testuser@nofoobar.com",
        "email": "testing",
        "external_id": "external_id",
        "fl_id": 123,
    }
    response = client.post("/users/", json=json.dumps(data))
    response = client.get("/users/1")
    assert response.status_code == 200


my_config = Config(region_name="us-east-1")


@mock_cognitoidp
def test_cognito_authorization_process():
    password = "SecurePassword1234#$%"
    username = "test.user@willdom.com"
    cognito_client = boto3.client("cognito-idp", config=my_config)
    user_pool_id = cognito_client.create_user_pool(PoolName="TestUserPool")["UserPool"]["Id"]
    cognito_client.create_user_pool_client(UserPoolId=user_pool_id, ClientName="TestAppClient")

    response = cognito_client.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        TemporaryPassword=password,
        UserAttributes=[{"Name": "email", "Value": username}],
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
