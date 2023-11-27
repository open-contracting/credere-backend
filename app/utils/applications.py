import logging
from datetime import datetime
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, defaultload, joinedload

from app import models, util

logger = logging.getLogger(__name__)

OCP_cannot_modify = [
    models.ApplicationStatus.LAPSED,
    models.ApplicationStatus.DECLINED,
    models.ApplicationStatus.APPROVED,
    models.ApplicationStatus.CONTRACT_UPLOADED,
    models.ApplicationStatus.COMPLETED,
    models.ApplicationStatus.REJECTED,
]


document_type_keys = [doc_type.name for doc_type in models.BorrowerDocumentType]


def get_application_by_uuid(uuid: str, session: Session) -> models.Application:
    """
    Retrieve an application by its UUID from the database.

    This function queries the database to find an application that matches the given UUID.
    It raises an HTTPException if no such application is found or if the application's status is LAPSED.

    :param uuid: The UUID of the application.
    :type uuid: str

    :param session: The database session.
    :type session: Session

    :return: The application that matches the UUID.
    :rtype: models.Application

    :raise HTTPException: If no application matches the UUID or if the application's status is LAPSED.
    """
    application = (
        models.Application.filter_by(session, "uuid", uuid)
        .options(
            defaultload(models.Application.borrower),
            defaultload(models.Application.award),
            defaultload(models.Application.borrower_documents),
        )
        .first()
    )
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    if application.status == models.ApplicationStatus.LAPSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=util.ERROR_CODES.APPLICATION_LAPSED.value,
        )

    return application


def get_application_by_id(id: int, session: Session) -> models.Application:
    """
    Retrieve an application by its ID from the database.

    This function queries the database to find an application that matches the given ID.
    It raises an HTTPException if no such application is found.

    :param id: The ID of the application.
    :type id: int

    :param session: The database session.
    :type session: Session

    :return: The application that matches the ID.
    :rtype: models.Application

    :raise HTTPException: If no application matches the ID.
    """
    application = (
        models.Application.filter_by(session, "id", id)
        .options(joinedload(models.Application.borrower), joinedload(models.Application.award))
        .first()
    )
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    return application


def check_is_application_expired(application: models.Application):
    expired_at = application.expired_at

    if not expired_at:
        return

    current_time = datetime.now(expired_at.tzinfo)

    if application.expired_at < current_time:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Application expired",
        )


def check_application_status(
    application: models.Application,
    applicationStatus: models.ApplicationStatus,
):
    """
    Check whether the application has expired.

    This function checks the expiration time of the provided application. It raises an HTTPException
    if the application has expired.

    :param application: The application to check.
    :type application: models.Application

    :raise HTTPException: If the application has expired.
    """
    if application.status != applicationStatus:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Application status is not {}".format(applicationStatus.name),
        )


def check_application_in_status(
    application: models.Application,
    applicationStatus: List[models.ApplicationStatus],
):
    """
    Check if the application's status is among a provided list of statuses.

    This function checks if the status of the given application is in a list of allowed statuses.
    If the status is not in the list, it raises an HTTPException.

    :param application: The application to check.
    :type application: models.Application

    :param applicationStatus: A list of allowed application statuses.
    :type applicationStatus: List[models.ApplicationStatus]

    :param detail: A custom error message to provide in case the status is not in the list.
                If not provided, a default error message is used.
    :type detail: str, optional

    :raise HTTPException: If the application's status is not in the provided list.
    """

    if application.status not in applicationStatus:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Application status should not be {}".format(application.status.name),
        )


def check_application_not_status(
    application: models.Application,
    applicationStatus: List[models.ApplicationStatus],
):
    """
    Check if the application's status is not among a provided list of statuses.

    This function checks if the status of the given application is not in a list of disallowed statuses.
    If the status is in the list, it raises an HTTPException.

    :param application: The application to check.
    :type application: models.Application

    :param applicationStatus: A list of disallowed application statuses.
    :type applicationStatus: List[models.ApplicationStatus]

    :param detail: A custom error message to provide in case the status is in the list.
                If not provided, a default error message is used.
    :type detail: str, optional

    :raise HTTPException: If the application's status is in the disallowed list.
    """

    if application.status in applicationStatus:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Application status is {}".format(application.status.name),
        )


def check_FI_user_permission(application: models.Application, user: models.User) -> None:
    if application.lender_id != user.lender_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not authorized",
        )


def check_FI_user_permission_or_OCP(application: models.Application, user: models.User) -> None:
    """
    Checks if a user has permission to interact with a given application.

    This function checks if the lender_id associated with the application matches the lender_id of the provided user.
    If they do not match, it raises an HTTPException with a 401 status code (Unauthorized).

    :param application: The application to check.
    :type application: models.Application

    :param user: The user to check.
    :type user: models.User

    :raises HTTPException: If the lender_id of the application and user do not match.
    """

    if not user.is_OCP() and application.lender_id != user.lender_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not authorized",
        )
