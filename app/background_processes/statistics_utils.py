from sqlalchemy import func, or_
from sqlalchemy.exc import SQLAlchemyError

from app.schema.core import Application, ApplicationStatus


def get_ocp_statistics(session):
    try:
        # Querys for OCP User
        total_applications_received = (
            session.query(Application)
            .filter(
                or_(
                    Application.status == ApplicationStatus.STARTED,
                    Application.status == ApplicationStatus.INFORMATION_REQUESTED,
                ),
            )
            .count()
        )
        total_applications_approved = (
            session.query(Application)
            .filter(
                or_(Application.status == ApplicationStatus.APPROVED),
            )
            .count()
        )
        total_applications_rejected = (
            session.query(Application)
            .filter(
                or_(Application.status == ApplicationStatus.REJECTED),
            )
            .count()
        )
        total_applications_waiting_for_information = (
            session.query(Application)
            .filter(
                or_(Application.status == ApplicationStatus.INFORMATION_REQUESTED),
            )
            .count()
        )

        ocp_statistics = {
            "total_applications_received": total_applications_received or 0,
            "total_applications_approved": total_applications_approved or 0,
            "total_applications_rejected": total_applications_rejected or 0,
            "total_applications_waiting_for_information": total_applications_waiting_for_information
            or 0,
        }

    except SQLAlchemyError as e:
        raise e

    return ocp_statistics


def get_fi_statistics(session):
    try:
        # Querys for FI user
        applications_received_by_lender = (
            session.query(Application.lender_id, func.count(Application.lender_id))
            .filter(
                or_(
                    Application.status == ApplicationStatus.STARTED,
                    Application.status == ApplicationStatus.INFORMATION_REQUESTED,
                )
            )
            .group_by(Application.lender_id)
            .all()
        )
        applications_approved_by_lender = (
            session.query(Application.lender_id, func.count(Application.lender_id))
            .filter(
                or_(
                    Application.status == ApplicationStatus.APPROVED,
                )
            )
            .group_by(Application.lender_id)
            .all()
        )
        applications_rejected_by_lender = (
            session.query(Application.lender_id, func.count(Application.lender_id))
            .filter(
                or_(
                    Application.status == ApplicationStatus.APPROVED,
                )
            )
            .group_by(Application.lender_id)
            .all()
        )
        applications_waiting_for_information_by_lender = (
            session.query(Application.lender_id, func.count(Application.lender_id))
            .filter(
                or_(
                    Application.status == ApplicationStatus.INFORMATION_REQUESTED,
                )
            )
            .group_by(Application.lender_id)
            .all()
        )
        fi_statistics = {
            "applications_received_by_lender": dict(applications_received_by_lender),
            "applications_approved_by_lender": dict(applications_approved_by_lender),
            "applications_rejected_by_lender": dict(applications_rejected_by_lender),
            "applications_waiting_for_information_by_lender": dict(
                applications_waiting_for_information_by_lender
            )
            if applications_received_by_lender
            else {},
        }
    except SQLAlchemyError as e:
        raise e

    return fi_statistics
