from contextlib import contextmanager
from datetime import datetime, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, joinedload

from app import models, util
from app.background_processes import background_utils
from app.db import get_db
from app.exceptions import SkippedAwardError
from app.settings import app_settings

DAYS_UNTIL_EXPIRED = 7

ApplicationStatus = models.ApplicationStatus


def create_application(
    award_id, borrower_id, email, legal_identifier, source_contract_id, session: Session
) -> models.Application:
    """
    Create a new application and insert it into the database.

    :param award_id: The ID of the award associated with the application.
    :type award_id: int
    :param borrower_id: The ID of the borrower associated with the application.
    :type borrower_id: int
    :param email: The email of the borrower.
    :type email: str
    :param legal_identifier: The legal identifier of the borrower.
    :type legal_identifier: str
    :param source_contract_id: The ID of the source contract.
    :type source_contract_id: str
    :param session: The database session.
    :type session: Session

    :return: The created application.
    :rtype: models.Application
    """
    award_borrower_identifier: str = background_utils.get_secret_hash(legal_identifier + source_contract_id)

    application = models.Application.first_by(session, "award_borrower_identifier", award_borrower_identifier)
    if application:
        raise SkippedAwardError(f"{application.id=} already exists for {legal_identifier=} {source_contract_id=}")

    new_uuid: str = util.generate_uuid(award_borrower_identifier)
    data = {
        "award_id": award_id,
        "borrower_id": borrower_id,
        "primary_email": email,
        "award_borrower_identifier": award_borrower_identifier,
        "uuid": new_uuid,
        "expired_at": datetime.utcnow() + timedelta(days=app_settings.application_expiration_days),
    }

    return models.Application.create(session, **data)


def get_dated_applications(session):
    """
    Get applications that meet specific date-based criteria.

    :param session: The database session.
    :type session: Session

    :return: A list of applications that meet the date-based criteria.
    :rtype: list[models.Application]
    """
    applications_to_remove_data = (
        session.query(models.Application)
        .options(
            joinedload(models.Application.borrower),
            joinedload(models.Application.borrower_documents),
        )
        .filter(
            or_(
                and_(
                    models.Application.status == ApplicationStatus.DECLINED,
                    models.Application.borrower_declined_at + timedelta(days=app_settings.days_to_erase_borrower_data)
                    < datetime.now(),
                ),
                and_(
                    models.Application.status == ApplicationStatus.REJECTED,
                    models.Application.lender_rejected_at + timedelta(days=app_settings.days_to_erase_borrower_data)
                    < datetime.now(),
                ),
                and_(
                    models.Application.status == ApplicationStatus.COMPLETED,
                    models.Application.lender_approved_at + timedelta(days=app_settings.days_to_erase_borrower_data)
                    < datetime.now(),
                ),
                and_(
                    models.Application.status == ApplicationStatus.LAPSED,
                    models.Application.application_lapsed_at + timedelta(days=app_settings.days_to_erase_borrower_data)
                    < datetime.now(),
                ),
            ),
            models.Application.archived_at.is_(None),
        )
        .all()
    )

    return applications_to_remove_data or []


def get_lapsed_applications(session):
    """
    Get applications that meet specific lapsed status criteria.

    :param session: The database session.
    :type session: Session

    :return: A list of applications that meet the lapsed status criteria.
    :rtype: list[models.Application]
    """
    applications_to_set_to_lapsed = (
        session.query(models.Application)
        .options(
            joinedload(models.Application.borrower),
            joinedload(models.Application.borrower_documents),
        )
        .filter(
            or_(
                and_(
                    models.Application.status == ApplicationStatus.PENDING,
                    models.Application.created_at + timedelta(days=app_settings.days_to_change_to_lapsed)
                    < datetime.now(),
                ),
                and_(
                    models.Application.status == ApplicationStatus.ACCEPTED,
                    models.Application.borrower_accepted_at + timedelta(days=app_settings.days_to_change_to_lapsed)
                    < datetime.now(),
                ),
                and_(
                    models.Application.status == ApplicationStatus.INFORMATION_REQUESTED,
                    models.Application.information_requested_at + timedelta(days=app_settings.days_to_change_to_lapsed)
                    < datetime.now(),
                ),
            ),
            models.Application.archived_at.is_(None),
        )
        .all()
    )

    return applications_to_set_to_lapsed or []


def get_applications_to_remind_intro(db_provider: Session = get_db):
    """
    Get applications that need a reminder for the introduction.

    :return: A list of applications that need an introduction reminder.
    :rtype: list[models.Application]
    """
    with contextmanager(db_provider)() as session:
        subquery = select(models.Message.application_id).where(
            models.Message.type == models.MessageType.BORROWER_PENDING_APPLICATION_REMINDER
        )
        users = (
            session.query(models.Application)
            .join(models.Borrower, models.Application.borrower_id == models.Borrower.id)
            .join(models.Award, models.Application.award_id == models.Award.id)
            .options(
                joinedload(models.Application.borrower),
                joinedload(models.Application.award),
            )
            .filter(
                and_(
                    models.Application.status == ApplicationStatus.PENDING,
                    models.Application.expired_at > datetime.now(),
                    models.Application.expired_at
                    <= datetime.now() + timedelta(days=app_settings.reminder_days_before_expiration),
                    ~models.Application.id.in_(subquery),
                    models.Borrower.status == models.BorrowerStatus.ACTIVE,
                )
            )
            .all()
        )

    return users or []


def get_applications_to_remind_submit(db_provider: Session = get_db):
    """
    Get applications that need a reminder to submit.

    :return: A list of applications that need a submit reminder.
    :rtype: list[models.Application]
    """
    with contextmanager(db_provider)() as session:
        subquery = select(models.Message.application_id).where(
            models.Message.type == models.MessageType.BORROWER_PENDING_SUBMIT_REMINDER
        )
        users = (
            session.query(models.Application)
            .options(
                joinedload(models.Application.borrower),
                joinedload(models.Application.award),
            )
            .filter(
                and_(
                    models.Application.status == ApplicationStatus.ACCEPTED,
                    models.Application.expired_at > datetime.now(),
                    models.Application.expired_at
                    <= datetime.now() + timedelta(days=app_settings.reminder_days_before_expiration),
                    ~models.Application.id.in_(subquery),
                )
            )
            .all()
        )

    return users or []


def get_all_applications_with_status(status_list, session):
    """
    Get all applications that have one of the specified status.

    :param status_list: The list of status to filter applications.
    :type status_list: list[models.ApplicationStatus]
    :param session: The database session.
    :type session: Session

    :return: A list of applications that have the specified status.
    :rtype: list[models.Application]
    """
    applications = session.query((models.Application)).filter(models.Application.status.in_(status_list)).all()

    return applications


def get_application_days_passed(application: models.Application, session: Session):
    """
    Calculate the number of days passed between different application actions.

    :param application: The application to calculate the days passed for.
    :type application: models.Application
    :param session: The database session.
    :type session: Session

    :return: The number of days passed between application actions.
    :rtype: int
    """
    paired_actions = []
    fi_request_actions = (
        session.query(models.ApplicationAction)
        .filter(models.ApplicationAction.application_id == application.id)
        .filter(models.ApplicationAction.type == models.ApplicationActionType.FI_REQUEST_INFORMATION)
        .order_by(models.ApplicationAction.created_at)
        .all()
    )
    if fi_request_actions:
        first_information_request = fi_request_actions.pop(0)
        paired_actions.append(
            (
                first_information_request.created_at,
                application.lender_started_at,
            )
        )
    else:
        current_dt = datetime.now(application.created_at.tzinfo)
        paired_actions.append(
            (
                current_dt,
                application.lender_started_at,
            )
        )

    msme_upload_actions = (
        session.query(models.ApplicationAction)
        .filter(models.ApplicationAction.application_id == application.id)
        .filter(
            models.ApplicationAction.type == models.ApplicationActionType.MSME_UPLOAD_ADDITIONAL_DOCUMENT_COMPLETED
        )
        .order_by(models.ApplicationAction.created_at)
        .all()
    )

    for msme_upload_action in msme_upload_actions:
        if not fi_request_actions:
            current_dt = datetime.now(application.created_at.tzinfo)
            paired_actions.append((current_dt, msme_upload_action.created_at))
            break
        else:
            fi_request_action = fi_request_actions.pop(0)
            paired_actions.append(
                (
                    fi_request_action.created_at,
                    msme_upload_action.created_at,
                )
            )

    days_passed = 0
    for fi_request_action, msme_upload_action in paired_actions:
        days_passed += (fi_request_action - msme_upload_action).days
    days_passed = round(days_passed)
    return days_passed
