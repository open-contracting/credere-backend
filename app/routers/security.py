from fastapi import APIRouter, Depends

from ..utils.verify_token import get_current_user, verifyTokeClass

authorizedCredentials = verifyTokeClass()

router = APIRouter()


@router.get("/secure-endpoint-example", dependencies=[Depends(authorizedCredentials)])
def example_of_secure_endpoint():
    return {"message": "OK"}


@router.get(
    "/secure-endpoint-example-username-extraction",
    dependencies=[Depends(authorizedCredentials)],
)
def example_of_secure_endpoint_with_username(
    usernameFromToken: str = Depends(get_current_user),
):
    return {"username": usernameFromToken}
