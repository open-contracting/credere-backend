from datetime import datetime

from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError

from app.schema.core import Application, ApplicationStatus


def get_general_statistics(session, start_date=None, end_date=None, lender_id=None):
    if start_date is None:
        start_date = "2023-01-01"
    if end_date is None:
        end_date = datetime.now()
    try:
        # received--------
        applications_aproved_query = session.query(Application).filter(
            and_(
                Application.created_at >= start_date,
                Application.created_at <= end_date,
                Application.borrower_submitted_at.isnot(None),
            )
        )
        if lender_id is not None:
            applications_aproved_query = applications_aproved_query.filter(
                Application.lender_id == lender_id
            )
        applications_received_count = applications_aproved_query.count()

        # approved-------
        applications_aproved_query = session.query(Application).filter(
            and_(
                Application.created_at >= start_date,
                Application.created_at <= end_date,
                Application.status == ApplicationStatus.APPROVED,
            )
        )
        if lender_id is not None:
            applications_aproved_query = applications_aproved_query.filter(
                Application.lender_id == lender_id
            )
        applications_aproved_count = applications_aproved_query.count()

        # rejected--------
        applications_rejected_query = session.query(Application).filter(
            and_(
                Application.created_at >= start_date,
                Application.created_at <= end_date,
                Application.status == ApplicationStatus.REJECTED,
            )
        )
        if lender_id is not None:
            applications_rejected_query = applications_rejected_query.filter(
                Application.lender_id == lender_id
            )
        applications_rejected_count = applications_rejected_query.count()

        # waiting---------
        applications_waiting_query = session.query(Application).filter(
            and_(
                Application.created_at >= start_date,
                Application.created_at <= end_date,
                Application.status == ApplicationStatus.REJECTED,
            )
        )
        if lender_id is not None:
            applications_waiting_query = applications_waiting_query.filter(
                Application.lender_id == lender_id
            )
        applications_waiting_count = applications_waiting_query.count()

        general_statistics = {
            "total_applications_received": applications_received_count or 0,
            "total_applications_approved": applications_aproved_count or 0,
            "total_applications_rejected": applications_rejected_count or 0,
            "total_applications_waiting_for_information": applications_waiting_count
            or 0,
        }

    except SQLAlchemyError as e:
        raise e

    return general_statistics


# def get_fi_statistics(session, start_date="2023-01-01", end_date=datetime.now()):
#     try:
#         # Querys for FI user
#         # creo que deberia se todos los estados menos pending
#         applications_received_by_lender = (
#             session.query(Application.lender_id, func.count(Application.lender_id))
#             .filter(
#                 and_(
#                     Application.created_at >= start_date,
#                     Application.created_at <= end_date,
#                     Application.borrower_submitted_at.isnot(None),
#                 )
#             )
#             .group_by(Application.lender_id)
#             .all()
#         )
#         applications_approved_by_lender = (
#             session.query(Application.lender_id, func.count(Application.lender_id))
#             .filter(
#                 and_(
#                     Application.created_at >= start_date,
#                     Application.created_at <= end_date,
#                     or_(
#                         Application.status == ApplicationStatus.APPROVED,
#                     ),
#                 )
#             )
#             .group_by(Application.lender_id)
#             .all()
#         )
#         applications_rejected_by_lender = (
#             session.query(Application.lender_id, func.count(Application.lender_id))
#             .filter(
#                 and_(
#                     Application.created_at >= start_date,
#                     Application.created_at <= end_date,
#                     or_(
#                         Application.status == ApplicationStatus.APPROVED,
#                     ),
#                 )
#             )
#             .group_by(Application.lender_id)
#             .all()
#         )
#         applications_waiting_for_information_by_lender = (
#             session.query(Application.lender_id, func.count(Application.lender_id))
#             .filter(
#                 and_(
#                     Application.created_at >= start_date,
#                     Application.created_at <= end_date,
#                     or_(
#                         Application.status == ApplicationStatus.INFORMATION_REQUESTED,
#                     ),
#                 )
#             )
#             .group_by(Application.lender_id)
#             .all()
#         )
#         fi_statistics = {
#             "applications_received_by_lender": dict(applications_received_by_lender),
#             "applications_approved_by_lender": dict(applications_approved_by_lender),
#             "applications_rejected_by_lender": dict(applications_rejected_by_lender),
#             "applications_waiting_for_information_by_lender": dict(
#                 applications_waiting_for_information_by_lender
#             )
#             if applications_received_by_lender
#             else {},
#         }
#     except SQLAlchemyError as e:
#         raise e

# return fi_statistics
