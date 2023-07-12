from datetime import datetime

from sqlalchemy import Integer, and_, distinct, func, or_, text
from sqlalchemy.exc import SQLAlchemyError

from app.schema.core import Application, ApplicationStatus, Borrower


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
        applications_approved_count = applications_aproved_query.count()

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

        # in progress---------
        applications_in_progress_query = session.query(Application).filter(
            and_(
                Application.created_at >= start_date,
                Application.created_at <= end_date,
                Application.status == ApplicationStatus.REJECTED,
                or_(
                    Application.status == ApplicationStatus.REJECTED,
                    Application.status == ApplicationStatus.STARTED,
                    Application.status == ApplicationStatus.SUBMITTED,
                    Application.status == ApplicationStatus.CONTRACT_UPLOADED,
                    Application.status == ApplicationStatus.INFORMATION_REQUESTED,
                ),
            )
        )
        if lender_id is not None:
            applications_in_progress_query = applications_waiting_query.filter(
                Application.lender_id == lender_id
            )
        applications_in_progress_count = applications_in_progress_query.count()

        # credit disbursed---------
        applications_with_credit_disbursed = session.query(Application).filter(
            and_(
                Application.created_at >= start_date,
                Application.created_at <= end_date,
                Application.disbursed_final_amount.isnot(None),
            )
        )
        if lender_id is not None:
            applications_with_credit_disbursed = applications_waiting_query.filter(
                Application.lender_id == lender_id
            )
        applications_with_credit_disbursed_count = (
            applications_with_credit_disbursed.count()
        )

        # credit disbursed %---------
        if (
            applications_approved_count == 0
            or applications_with_credit_disbursed_count == 0
        ):
            proportion_of_disbursed = 0
        else:
            proportion_of_disbursed = (
                applications_with_credit_disbursed_count / applications_approved_count
            ) * 100

        # Average amount requested
        average_amount_requested_query = session.query(
            func.avg(Application.amount_requested)
        ).filter(
            and_(
                Application.created_at >= start_date,
                Application.created_at <= end_date,
                Application.amount_requested.isnot(None),
            )
        )

        if lender_id is not None:
            average_amount_requested_query = average_amount_requested_query.filter(
                Application.lender_id == lender_id
            )

        average_amount_requested = average_amount_requested_query.scalar()

        # Average Repayment Period
        average_repayment_period_query = session.query(
            func.avg(
                Application.repayment_years * 12 + Application.repayment_months
            ).cast(Integer)
        ).filter(
            and_(
                Application.created_at >= start_date,
                Application.created_at <= end_date,
                # OJO PENDIENTE CONFIRMAR SI SE VA A PONER 0 EN CASO DE QUE NO SE COMPLETE NADA O SE VA DEJAR NULL
                # SI SE DEJA NULL TENGO QUE CAMBIAR ESTE QUERY
                Application.repayment_years.isnot(None),
                Application.repayment_months.isnot(None),
            )
        )

        if lender_id is not None:
            average_repayment_period_query = average_repayment_period_query.filter(
                Application.lender_id == lender_id
            )

        average_repayment_period = average_repayment_period_query.scalar()

        general_statistics = {
            "applications_received_count": applications_received_count,
            "applications_approved_count": applications_approved_count,
            "applications_rejected_count": applications_rejected_count,
            "applications_waiting_for_information_count": applications_waiting_count,
            "applications_in_progress_count": applications_in_progress_count,
            "applications_with_credit_disbursed_count": applications_with_credit_disbursed_count,
            "proportion_of_disbursed": proportion_of_disbursed,
            "average_amount_requested": average_amount_requested,
            "average_repayment_period": average_repayment_period,
        }

    except SQLAlchemyError as e:
        raise e

    return general_statistics


def get_msme_opt_in_stats(session):
    try:
        # opt in--------
        opt_in_query = session.query(Application).filter(
            and_(
                Application.borrower_accepted_at.isnot(None),
            )
        )

        # opt in %--------
        opt_in_percentage = (
            session.query(Application)
            .filter(Application.borrower_accepted_at.isnot(None))
            .count()
            / session.query(Application).count()
        ) * 100

        opt_in_query_count = opt_in_query.count()

        # opt proportion by sector %--------
        # Calculate total submitted application count
        total_submitted_application_count = (
            session.query(Application)
            .filter(Application.borrower_submitted_at.isnot(None))
            .count()
        )
        print(total_submitted_application_count)
        sectors = (
            session.query(
                Borrower.sector, func.count(distinct(Application.id)).label("count")
            )
            .join(Application, Borrower.id == Application.borrower_id)
            .filter(Application.borrower_accepted_at.isnot(None))
            .group_by(Borrower.sector)
            .all()
        )

        sector_statistics = {}
        for sector, count in sectors:
            sector_statistics[sector] = round(
                count / total_submitted_application_count * 100
            )

        # Count of Declined reasons
        declined_applications = session.query(Application).filter(
            Application.borrower_declined_at.isnot(None)
        )

        # Count occurrences for each case
        dont_need_access_credit_count = declined_applications.filter(
            text(
                "(borrower_declined_preferences_data->>'dont_need_access_credit')::boolean is True"
            )
        ).count()

        already_have_acredit_count = declined_applications.filter(
            text(
                "(borrower_declined_preferences_data->>'already_have_acredit')::boolean is True"
            )
        ).count()

        preffer_to_go_to_bank_count = declined_applications.filter(
            text(
                "(borrower_declined_preferences_data->>'preffer_to_go_to_bank')::boolean is True"
            )
        ).count()

        dont_want_access_credit_count = declined_applications.filter(
            text(
                "(borrower_declined_preferences_data->>'dont_want_access_credit')::boolean is True"
            )
        ).count()

        other_count = declined_applications.filter(
            text("(borrower_declined_preferences_data->>'other')::boolean is True")
        ).count()

        rejected_reasons_count_by_reason = {
            "dont_need_access_credit_count": dont_need_access_credit_count,
            "already_have_acredit_count": already_have_acredit_count,
            "preffer_to_go_to_bank_count": preffer_to_go_to_bank_count,
            "dont_want_access_credit_count": dont_want_access_credit_count,
            "other_count": other_count,
        }

        opt_in_statistics = {
            "opt_in_query_count": opt_in_query_count,
            "opt_in_percentage": opt_in_percentage,
            "sector_statistics": sector_statistics,
            "rejected_reasons_count_by_reason": rejected_reasons_count_by_reason,
        }

    except SQLAlchemyError as e:
        raise e

    return opt_in_statistics
