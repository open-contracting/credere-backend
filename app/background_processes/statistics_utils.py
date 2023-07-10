import logging

from sqlalchemy import func, or_
from sqlalchemy.exc import SQLAlchemyError

from app.schema.core import Application, ApplicationStatus


def get_statistics(session):
    try:
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

        logging.info(total_applications_received)
        logging.info(applications_received_by_lender)
    except SQLAlchemyError as e:
        raise e
    # I need to return the dictionary
    result = {
        "total_applications_received": total_applications_received or 0,
        "applications_received_by_lender": dict(applications_received_by_lender)
        if applications_received_by_lender
        else {},
    }
    return result
