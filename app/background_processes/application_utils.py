from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.core.user_dependencies import sesClient
from app.db.session import app_settings, get_db, transaction_session
from app.schema import core
from app.utils import email_utility

from . import background_utils

ApplicationStatus = core.ApplicationStatus


DAYS_UNTIL_EXPIRED = 7

ApplicationStatus = core.ApplicationStatus


def insert_application(application: core.Application, session: Session):
    """
    Insert a new application into the database.

    :param application: The application data to be inserted.
    :type application: core.Application
    :param session: The database session.
    :type session: Session

    :return: The inserted application.
    :rtype: core.Application
    """
    obj_db = core.Application(**application)
    obj_db.created_at = datetime.utcnow()

    session.add(obj_db)
    session.flush()

    return obj_db


def insert_message(application: core.Application, session: Session):
    """
    Insert a new message associated with an application into the database.

    :param application: The application to associate the message with.
    :type application: core.Application
    :param session: The database session.
    :type session: Session

    :return: The inserted message.
    :rtype: core.Message
    """
    obj_db = core.Message(
        application=application, type=core.MessageType.BORROWER_INVITACION
    )
    obj_db.created_at = datetime.utcnow()

    session.add(obj_db)
    session.flush()

    return obj_db


def get_existing_application(award_borrower_identifier: str, session: Session):
    """
    Get an existing application based on the award borrower identifier.

    :param award_borrower_identifier: The unique identifier for the award and borrower combination.
    :type award_borrower_identifier: str
    :param session: The database session.
    :type session: Session

    :return: The existing application if found, otherwise None.
    :rtype: core.Application or None
    """
    application = (
        session.query(core.Application)
        .filter(core.Application.award_borrower_identifier == award_borrower_identifier)
        .first()
    )

    return application


def create_application(
    award_id, borrower_id, email, legal_identifier, source_contract_id, session: Session
) -> core.Application:
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
    :rtype: core.Application
    """
    award_borrower_identifier: str = background_utils.get_secret_hash(
        legal_identifier + source_contract_id
    )

    # if application already exists
    application = get_existing_application(award_borrower_identifier, session)
    if application:
        error_data = {
            "legal_identifier": legal_identifier,
            "source_contract_id": source_contract_id,
            "application_id": application.id,
        }

        background_utils.raise_sentry_error(
            f"Skipping Award - Application ID {application.id} already exists on for award {source_contract_id}",
            error_data,
        )

    new_uuid: str = background_utils.generate_uuid(award_borrower_identifier)
    application = {
        "award_id": award_id,
        "borrower_id": borrower_id,
        "primary_email": email,
        "award_borrower_identifier": award_borrower_identifier,
        "uuid": new_uuid,
        "expired_at": datetime.utcnow()
        + timedelta(days=app_settings.application_expiration_days),
    }

    application = insert_application(application, session)

    return application


def get_dated_applications(session):
    """
    Get applications that meet specific date-based criteria.

    :param session: The database session.
    :type session: Session

    :return: A list of applications that meet the date-based criteria.
    :rtype: list[core.Application]
    """
    try:
        applications_to_remove_data = (
            session.query(core.Application)
            .options(
                joinedload(core.Application.borrower),
                joinedload(core.Application.borrower_documents),
            )
            .filter(
                or_(
                    and_(
                        core.Application.status == ApplicationStatus.DECLINED,
                        core.Application.borrower_declined_at
                        + timedelta(days=app_settings.days_to_erase_borrower_data)
                        < datetime.now(),
                    ),
                    and_(
                        core.Application.status == ApplicationStatus.REJECTED,
                        core.Application.lender_rejected_at
                        + timedelta(days=app_settings.days_to_erase_borrower_data)
                        < datetime.now(),
                    ),
                    and_(
                        core.Application.status == ApplicationStatus.COMPLETED,
                        core.Application.lender_approved_at
                        + timedelta(days=app_settings.days_to_erase_borrower_data)
                        < datetime.now(),
                    ),
                    and_(
                        core.Application.status == ApplicationStatus.LAPSED,
                        core.Application.application_lapsed_at
                        + timedelta(days=app_settings.days_to_erase_borrower_data)
                        < datetime.now(),
                    ),
                ),
                core.Application.archived_at.is_(None),
            )
            .all()
        )
    except SQLAlchemyError as e:
        raise e

    return applications_to_remove_data or []


def get_lapsed_applications(session):
    """
    Get applications that meet specific lapsed status criteria.

    :param session: The database session.
    :type session: Session

    :return: A list of applications that meet the lapsed status criteria.
    :rtype: list[core.Application]
    """
    try:
        applications_to_set_to_lapsed = (
            session.query(core.Application)
            .options(
                joinedload(core.Application.borrower),
                joinedload(core.Application.borrower_documents),
            )
            .filter(
                or_(
                    and_(
                        core.Application.status == ApplicationStatus.PENDING,
                        core.Application.created_at
                        + timedelta(days=app_settings.days_to_change_to_lapsed)
                        < datetime.now(),
                    ),
                    and_(
                        core.Application.status == ApplicationStatus.ACCEPTED,
                        core.Application.borrower_accepted_at
                        + timedelta(days=app_settings.days_to_change_to_lapsed)
                        < datetime.now(),
                    ),
                    and_(
                        core.Application.status
                        == ApplicationStatus.INFORMATION_REQUESTED,
                        core.Application.information_requested_at
                        + timedelta(days=app_settings.days_to_change_to_lapsed)
                        < datetime.now(),
                    ),
                ),
                core.Application.archived_at.is_(None),
            )
            .all()
        )

    except SQLAlchemyError as e:
        raise e

    return applications_to_set_to_lapsed or []


def get_applications_to_remind_intro():
    """
    Get applications that need a reminder for the introduction.

    :return: A list of applications that need an introduction reminder.
    :rtype: list[core.Application]
    """
    with contextmanager(get_db)() as session:
        try:
            subquery = select(core.Message.application_id).where(
                core.Message.type
                == core.MessageType.BORROWER_PENDING_APPLICATION_REMINDER
            )
            users = (
                session.query(core.Application)
                .options(
                    joinedload(core.Application.borrower),
                    joinedload(core.Application.award),
                )
                .filter(
                    and_(
                        core.Application.status == ApplicationStatus.PENDING,
                        core.Application.expired_at > datetime.now(),
                        core.Application.expired_at
                        <= datetime.now()
                        + timedelta(days=app_settings.reminder_days_before_expiration),
                        ~core.Application.id.in_(subquery),
                        core.Borrower.status == core.BorrowerStatus.ACTIVE,
                    )
                )
                .all()
            )

        except SQLAlchemyError as e:
            raise e
    return users or []


def get_applications_to_remind_submit():
    """
    Get applications that need a reminder to submit.

    :return: A list of applications that need a submit reminder.
    :rtype: list[core.Application]
    """
    with contextmanager(get_db)() as session:
        try:
            subquery = select(core.Message.application_id).where(
                core.Message.type == core.MessageType.BORROWER_PENDING_SUBMIT_REMINDER
            )
            users = (
                session.query(core.Application)
                .options(
                    joinedload(core.Application.borrower),
                    joinedload(core.Application.award),
                )
                .filter(
                    and_(
                        core.Application.status == ApplicationStatus.ACCEPTED,
                        core.Application.expired_at > datetime.now(),
                        core.Application.expired_at
                        <= datetime.now()
                        + timedelta(days=app_settings.reminder_days_before_expiration),
                        ~core.Application.id.in_(subquery),
                    )
                )
                .all()
            )

        except SQLAlchemyError as e:
            raise e
    return users or []


def create_message(
    application: core.Application,
    message: core.MessageType,
    session: Session,
    external_message_id: str,
) -> None:
    """
    Create and insert a new message associated with an application.

    :param application: The application to associate the message with.
    :type application: core.Application
    :param message: The type of message to be created.
    :type message: core.MessageType
    :param session: The database session.
    :type session: Session
    :param external_message_id: The external message ID.
    :type external_message_id: str

    :return: None
    :rtype: None
    """
    obj_db = core.Message(
        application=application,
        type=message,
        external_message_id=external_message_id,
    )
    obj_db.created_at = datetime.utcnow()

    session.add(obj_db)
    session.flush()


def get_all_applications_with_status(status_list, session):
    """
    Get all applications that have one of the specified status.

    :param status_list: The list of status to filter applications.
    :type status_list: list[core.ApplicationStatus]
    :param session: The database session.
    :type session: Session

    :return: A list of applications that have the specified status.
    :rtype: list[core.Application]
    """
    applications = (
        session.query((core.Application))
        .filter(core.Application.status.in_(status_list))
        .all()
    )

    return applications


def get_application_days_passed(application: core.Application, session: Session):
    """
    Calculate the number of days passed between different application actions.

    :param application: The application to calculate the days passed for.
    :type application: core.Application
    :param session: The database session.
    :type session: Session

    :return: The number of days passed between application actions.
    :rtype: int
    """
    paired_actions = []
    fi_request_actions = (
        session.query(core.ApplicationAction)
        .filter(core.ApplicationAction.application_id == application.id)
        .filter(
            core.ApplicationAction.type
            == core.ApplicationActionType.FI_REQUEST_INFORMATION
        )
        .order_by(core.ApplicationAction.created_at)
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
        session.query(core.ApplicationAction)
        .filter(core.ApplicationAction.application_id == application.id)
        .filter(
            core.ApplicationAction.type
            == core.ApplicationActionType.MSME_UPLOAD_ADDITIONAL_DOCUMENT_COMPLETED
        )
        .order_by(core.ApplicationAction.created_at)
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


def send_overdue_reminders(session: Session):
    """
    Send reminders for applications that are overdue.

    :param session: The database session.
    :type session: Session

    :return: None
    :rtype: None
    """
    applications = get_all_applications_with_status(
        [
            core.ApplicationStatus.INFORMATION_REQUESTED,
            core.ApplicationStatus.STARTED,
        ],
        session,
    )
    overdue_lenders = defaultdict(lambda: {"count": 0})
    for application in applications:
        with transaction_session(session):
            days_passed = get_application_days_passed(application, session)
            if (
                days_passed
                > application.lender.sla_days
                * app_settings.progress_to_remind_started_applications
            ):
                if "email" not in overdue_lenders[application.lender.id]:
                    overdue_lenders[application.lender.id][
                        "email"
                    ] = application.lender.email_group
                    overdue_lenders[application.lender.id][
                        "name"
                    ] = application.lender.name
                overdue_lenders[application.lender.id]["count"] += 1
                if days_passed > application.lender.sla_days:
                    current_dt = datetime.now(application.created_at.tzinfo)
                    application.overdued_at = current_dt
                    message_id = email_utility.send_overdue_application_email_to_OCP(
                        sesClient,
                        application.lender.name,
                    )

                    create_message(
                        application,
                        core.MessageType.OVERDUE_APPLICATION,
                        session,
                        message_id,
                    )

    for id, lender_data in overdue_lenders.items():
        name = lender_data.get("name")
        count = lender_data.get("count")
        email = lender_data.get("email")
        message_id = email_utility.send_overdue_application_email_to_FI(
            sesClient, name, email, count
        )

        create_message(
            application,
            core.MessageType.OVERDUE_APPLICATION,
            session,
            message_id,
        )
        session.flush()
    session.commit()
