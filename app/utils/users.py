import logging
from datetime import datetime

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import asc, desc, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.user_dependencies import CognitoClient
from app.db.session import transaction_session
from app.schema.api import UserListResponse

from ..schema import core

logger = logging.getLogger(__name__)


def create_user(payload: core.User, session: Session, client: CognitoClient) -> core.User:
    """
    Creates a new user in the database and also in the Cognito User Pool.

    :param payload: The user data.
    :type payload: core.User

    :param session: The database session.
    :type session: Session

    :param client: The Cognito client.
    :type client: CognitoClient

    :return: The created user instance.
    :rtype: core.User

    :raises HTTPException: If the username already exists.
    """
    with transaction_session(session):
        try:
            user = core.User(**payload.dict())
            user.created_at = datetime.now()
            session.add(user)
            cognitoResponse = client.admin_create_user(payload.email, payload.name)
            user.external_id = cognitoResponse["User"]["Username"]

            return user
        except (client.exceptions().UsernameExistsException, IntegrityError) as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Username already exists",
            )


def update_user(session: Session, payload: dict, user_id: int) -> core.User:
    """
    Updates a user's details in the database.

    :param session: The database session.
    :type session: Session

    :param payload: The updated user data.
    :type payload: dict

    :param user_id: The ID of the user to update.
    :type user_id: int

    :return: The updated user instance.
    :rtype: core.User

    :raises HTTPException: If the user is not found or the username already exists.
    """
    try:
        user = session.query(core.User).filter(core.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        update_dict = jsonable_encoder(payload, exclude_unset=True)
        return user.update(session, **update_dict)
    except IntegrityError as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="User already exists",
        )


def get_all_users(page: int, page_size: int, sort_field: str, sort_order: str, session: Session) -> UserListResponse:
    """
    Retrieve all users in the system in a paginated and sorted manner.

    :param page: The page number (starting from 0) of the requested page of users.
    :type page: int

    :param page_size: The number of users to include on each page.
    :type page_size: int

    :param sort_field: The field to sort the users by.
    :type sort_field: str

    :param sort_order: The order to sort the users in. This should be either "asc" for ascending or "desc" for descending. # noqa: E501
    :type sort_order: str

    :param session: The database session.
    :type session: Session

    :return: A paginated and sorted list of all users, along with the total count of users.
    :rtype: UserListResponse
    """
    sort_direction = desc if sort_order.lower() == "desc" else asc

    list_query = (
        session.query(core.User)
        .outerjoin(core.Lender)
        .options(
            joinedload(core.User.lender),
        )
        .order_by(text(f"{sort_field} {sort_direction.__name__}"), core.User.id)
    )

    total_count = list_query.count()

    users = list_query.offset(page * page_size).limit(page_size).all()

    return UserListResponse(
        items=users,
        count=total_count,
        page=page,
        page_size=page_size,
    )
