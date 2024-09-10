import json
import os
from contextlib import contextmanager
from typing import Generator

from fastapi import status
from sqlalchemy.orm import Session, sessionmaker

from app import models
from app.settings import app_settings

BASEDIR = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


class MockResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self.json_data = json_data

    @property
    def text(self):
        return json.dumps(self.json_data)

    def json(self):
        return self.json_data


def load_json_file(filename):
    with open(os.path.join(BASEDIR, filename)) as f:
        return json.load(f)


def get_test_db(engine):
    factory = sessionmaker(expire_on_commit=False, bind=engine)

    def inner() -> Generator[Session, None, None]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    return inner


def create_user(session, aws_client, *, email, **kwargs):
    # create_user()
    response = aws_client.cognito.admin_create_user(
        UserPoolId=app_settings.cognito_pool_id,
        Username=email,
        TemporaryPassword="initial-autogenerated-password",
        MessageAction="SUPPRESS",
        UserAttributes=[{"Name": "email", "Value": email}],
    )
    user = models.User.create(session, email=email, **kwargs)
    user.external_id = response["User"]["Username"]
    session.commit()

    # User is sent a link to Credere frontend's /create-password path.

    # change_password()
    response = aws_client.initiate_auth(email, "initial-autogenerated-password")
    assert response.get("ChallengeName") == "NEW_PASSWORD_REQUIRED", response
    response = aws_client.respond_to_auth_challenge(
        username=email,
        session=response["Session"],
        challenge_name="NEW_PASSWORD_REQUIRED",
        new_password="12345-UPPER-lower",
    )
    aws_client.cognito.admin_update_user_attributes(
        UserPoolId=app_settings.cognito_pool_id,
        Username=email,
        UserAttributes=[{"Name": "email_verified", "Value": "true"}],
    )
    assert response.get("ChallengeName") == "MFA_SETUP", response
    response = aws_client.cognito.associate_software_token(Session=response["Session"])

    # setup_mfa()
    aws_client.cognito.verify_software_token(Session=response["Session"], UserCode="123456")

    # login()
    response = aws_client.initiate_auth(email, "12345-UPPER-lower")
    response = aws_client.respond_to_auth_challenge(
        email, session=response["Session"], challenge_name=response["ChallengeName"], mfa_code="123456"
    )

    return {"Authorization": "Bearer " + response["AuthenticationResult"]["AccessToken"]}


def assert_ok(response):
    assert response.status_code == status.HTTP_200_OK, f"{response.status_code}: {response.json()}"


def assert_success(result, stdout=""):
    assert result.exit_code == 0, result.exc_info
    assert result.stdout == stdout, f"{result.stdout!r} != {stdout!r}"  # CliRunner(mix_stderr=True) by default


@contextmanager
def assert_change(obj, attr, change):
    expected = getattr(obj, attr) + change
    yield
    actual = getattr(obj, attr)

    assert actual == expected, f"{actual} != {expected}"
