import base64
import hashlib
import hmac
import logging
import random
import string
from collections.abc import Callable

import boto3
from fastapi import HTTPException, status
from mypy_boto3_cognito_idp import CognitoIdentityProviderClient, literals, type_defs
from mypy_boto3_ses.client import SESClient

from app.i18n import _
from app.settings import app_settings

logger = logging.getLogger(__name__)

PASSWORD_LENGTH = 14
PASSWORD_CHARACTERS = list(
    set(string.ascii_letters) | set(string.digits) | set(string.punctuation) - set('"/\\|_-#@%&*(){}[]<>~`')
)


def generate_password_fn() -> str:
    """
    Return a random password of 14 ASCII letter, digit and punctuation characters.
    """
    return "".join(random.choice(PASSWORD_CHARACTERS) for _ in range(PASSWORD_LENGTH))  # noqa: S311


# https://docs.aws.amazon.com/cognito/latest/developerguide/signing-up-users-in-your-app.html#cognito-user-pools-computing-secret-hash
def get_secret_hash(username: str) -> str:
    """
    Generate a secret hash for the given username using Cognito client secret and Cognito client id.

    :param username: The username
    :return: A base64 encoded string containing the generated secret hash.
    """
    message = f"{username}{app_settings.cognito_client_id}".encode()
    key = app_settings.cognito_client_secret.encode()
    return base64.b64encode(hmac.new(key, message, digestmod=hashlib.sha256).digest()).decode()


class Client:
    """
    A client for Cognito and SES services.
    """

    def __init__(
        self,
        cognito_client: CognitoIdentityProviderClient,
        ses_client: SESClient,
        generate_password_fn: Callable[[], str],
    ):
        #: A boto3 client for Cognito
        self.cognito = cognito_client
        #: A boto3 client for SES
        self.ses = ses_client
        #: A function reference that generates a password
        self.generate_password = generate_password_fn

    def initiate_auth(self, username: str, password: str) -> type_defs.InitiateAuthResponseTypeDef:
        """
        Initiates an authentication request for a user in Cognito.

        :param username: The username (typically an email) of the user initiating authentication.
        :param password: The password of the user initiating the authentication.
        :return: The response from the Cognito 'initiate_auth' method, which includes the
                 session expiration time if the authentication is successful.
        :raises boto3.exceptions: Any exceptions that occur when making the Cognito request.
        """
        response = self.cognito.initiate_auth(
            ClientId=app_settings.cognito_client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password,
                "SECRET_HASH": get_secret_hash(username),
            },
        )

        # Extract the session expiration time from the response
        if "AuthenticationResult" in response:
            authentication_result = response["AuthenticationResult"]
            if "ExpiresIn" in authentication_result:
                expiration_time = authentication_result["ExpiresIn"]
                logger.info("Session expiration time (in seconds): %s", expiration_time)

        return response

    def respond_to_auth_challenge(
        self,
        username: str,
        session: str,
        challenge_name: literals.ChallengeNameTypeType,
        new_password: str = "",
        mfa_code: str = "",
    ) -> type_defs.RespondToAuthChallengeResponseTypeDef:
        """
        Responds to the authentication challenge provided by Cognito.

        :param username: The username (email) of the user.
        :param session: The session in which the user is currently authenticated.
        :param challenge_name: The name of the challenge to respond to.
        :param new_password: The new password of the user. This is required if the challenge is
                             'NEW_PASSWORD_REQUIRED'.
        :param mfa_code: The MFA code that was entered by the user. This is required if the
                         challenge is 'MFA_SETUP' or 'SOFTWARE_TOKEN_MFA'.
        :return: The response from the Cognito 'respond_to_auth_challenge' method.
        :raises boto3.exceptions: Any exceptions that occur when making the Cognito request.

        Notes:
            The 'respond_to_auth_challenge' method allows the application to respond to different types of
            authentication challenges issued by Cognito.

        """
        secret_hash = get_secret_hash(username)

        match challenge_name:
            case "NEW_PASSWORD_REQUIRED":
                return self.cognito.respond_to_auth_challenge(
                    ClientId=app_settings.cognito_client_id,
                    ChallengeName=challenge_name,
                    ChallengeResponses={
                        "USERNAME": username,
                        "NEW_PASSWORD": new_password,
                        "SECRET_HASH": secret_hash,
                    },
                    Session=session,
                )
            case "MFA_SETUP":
                associate_response = self.cognito.associate_software_token(Session=session)

                verify_response = self.cognito.verify_software_token(
                    AccessToken=associate_response["SecretCode"],
                    Session=associate_response["Session"],
                    UserCode=mfa_code,
                )

                return self.cognito.respond_to_auth_challenge(
                    ClientId=app_settings.cognito_client_id,
                    ChallengeName=challenge_name,
                    ChallengeResponses={
                        "USERNAME": username,
                        "NEW_PASSWORD": new_password,
                        "SECRET_HASH": secret_hash,
                    },
                    Session=verify_response["Session"],
                )
            case "SOFTWARE_TOKEN_MFA":
                return self.cognito.respond_to_auth_challenge(
                    ClientId=app_settings.cognito_client_id,
                    ChallengeName=challenge_name,
                    ChallengeResponses={
                        "USERNAME": username,
                        "SOFTWARE_TOKEN_MFA_CODE": mfa_code,
                        "SECRET_HASH": secret_hash,
                    },
                    Session=session,
                )
            case _:
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail=_("Authentication challenge not implemented"),
                )


ses_client = boto3.client(
    "ses",
    region_name=app_settings.aws_region,
    aws_access_key_id=app_settings.aws_access_key,
    aws_secret_access_key=app_settings.aws_client_secret,
)

client = Client(
    boto3.client(
        "cognito-idp",
        region_name=app_settings.aws_region,
        aws_access_key_id=app_settings.aws_access_key,
        aws_secret_access_key=app_settings.aws_client_secret,
    ),
    ses_client,
    generate_password_fn,
)
