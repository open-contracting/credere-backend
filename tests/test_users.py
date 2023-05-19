import boto3
from botocore.config import Config
from moto import mock_cognitoidp

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
