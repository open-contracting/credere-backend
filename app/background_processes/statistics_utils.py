# from datetime import datetime

from sqlalchemy import Integer, and_, distinct, func, or_, text
from sqlalchemy.exc import SQLAlchemyError

from app.schema.core import Application, ApplicationStatus  # noqa: F401 # isort:skip
from app.schema.core import Borrower, CreditProduct  # noqa: F401 # isort:skip
from app.schema.core import CreditType, StatisticData, Lender  # noqa: F401 # isort:skip


def get_base_query(sessionBase, start_date, end_date, lender_id):
    base_query = None
    if start_date is not None and end_date is not None:
        base_query = sessionBase.filter(
            and_(
                Application.created_at >= start_date,
                Application.created_at <= end_date,
            )
        )
    elif start_date is not None:
        base_query = sessionBase.filter(Application.created_at >= start_date)
    elif end_date is not None:
        base_query = sessionBase.filter(Application.created_at <= end_date)
    else:
        base_query = sessionBase

    if lender_id is not None:
        base_query = base_query.filter(Application.lender_id == lender_id)

    return base_query


def get_general_statistics(session, start_date=None, end_date=None, lender_id=None):
    try:
        # received--------
        applications_received_query = get_base_query(
            session.query(Application), start_date, end_date, lender_id
        ).filter(
            Application.borrower_submitted_at.isnot(None),
        )

        applications_received_count = applications_received_query.count()

        # approved-------
        applications_approved_query = get_base_query(
            session.query(Application), start_date, end_date, lender_id
        ).filter(
            or_(
                Application.status == ApplicationStatus.APPROVED,
                Application.status == ApplicationStatus.CONTRACT_UPLOADED,
                Application.status == ApplicationStatus.COMPLETED,
            ),
        )

        applications_approved_count = applications_approved_query.count()

        # rejected--------
        applications_rejected_query = get_base_query(
            session.query(Application), start_date, end_date, lender_id
        ).filter(
            Application.status == ApplicationStatus.REJECTED,
        )

        applications_rejected_count = applications_rejected_query.count()

        # waiting---------
        applications_waiting_query = get_base_query(
            session.query(Application), start_date, end_date, lender_id
        ).filter(
            Application.status == ApplicationStatus.INFORMATION_REQUESTED,
        )

        applications_waiting_count = applications_waiting_query.count()

        # in progress---------
        applications_in_progress_query = get_base_query(
            session.query(Application), start_date, end_date, lender_id
        ).filter(
            or_(
                Application.status == ApplicationStatus.STARTED,
                Application.status == ApplicationStatus.INFORMATION_REQUESTED,
            ),
        )

        applications_in_progress_count = applications_in_progress_query.count()

        # credit disbursed---------
        applications_with_credit_disbursed = get_base_query(
            session.query(Application), start_date, end_date, lender_id
        ).filter(
            Application.status == ApplicationStatus.COMPLETED,
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
            proportion_of_disbursed = int(
                applications_with_credit_disbursed_count
                / applications_approved_count
                * 100
            )

        # Average amount requested
        average_amount_requested_query = get_base_query(
            session.query(func.avg(Application.amount_requested)),
            start_date,
            end_date,
            lender_id,
        ).filter(
            Application.amount_requested.isnot(None),
        )

        average_amount_requested_result = average_amount_requested_query.scalar()
        average_amount_requested = (
            int(average_amount_requested_result)
            if average_amount_requested_result is not None
            else 0
        )

        # Average Repayment Period
        average_repayment_period_query = (
            get_base_query(
                session.query(
                    func.avg(
                        Application.repayment_years * 12 + Application.repayment_months
                    ).cast(Integer)
                ),
                start_date,
                end_date,
                lender_id,
            )
            .join(CreditProduct, Application.credit_product_id == CreditProduct.id)
            .filter(
                and_(
                    Application.borrower_submitted_at.isnot(None),
                    CreditProduct.type == CreditType.LOAN,
                )
            )
        )

        average_repayment_period = average_repayment_period_query.scalar() or 0

        # Overdue Application
        applications_overdue_query = get_base_query(
            session.query(Application), start_date, end_date, lender_id
        ).filter(
            Application.overdued_at.isnot(None),
        )

        applications_overdue_count = applications_overdue_query.count()

        # average time to process application
        average_processing_time_query = get_base_query(
            session.query(func.avg(Application.completed_in_days)),
            start_date,
            end_date,
            lender_id,
        ).filter(
            Application.status == ApplicationStatus.COMPLETED,
        )

        average_processing_time_result = average_processing_time_query.scalar()
        average_processing_time = (
            int(average_processing_time_result)
            if average_processing_time_result is not None
            else 0
        )
        #  get_proportion_of_submited_out_of_opt_in
        application_accepted_query = (
            get_base_query(session.query(Application), start_date, end_date, lender_id)
            .filter(Application.borrower_submitted_at.isnot(None))
            .count()
        )

        if lender_id is not None:
            application_divisor = (
                session.query(Application)
                .filter(Application.borrower_submitted_at.isnot(None))
                .count()
            )
        else:
            application_divisor = (
                session.query(Application)
                .filter(Application.borrower_accepted_at.isnot(None))
                .count()
            )

        # Calculate the proportion
        if application_accepted_query == 0:
            proportion_of_submitted_out_of_opt_in = 0
        else:
            proportion_of_submitted_out_of_opt_in = round(
                (application_accepted_query / application_divisor) * 100, 2
            )

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
            "applications_overdue_count": applications_overdue_count,
            "average_processing_time": average_processing_time,
            "proportion_of_submitted_out_of_opt_in": proportion_of_submitted_out_of_opt_in,
        }

    except SQLAlchemyError as e:
        raise e

    return general_statistics


# Group of Stat only for OCP USER (msme opt in stats)
def get_msme_opt_in_stats(session):
    try:
        # opt in--------
        opt_in_query = session.query(Application).filter(
            and_(
                Application.borrower_accepted_at.isnot(None),
            )
        )
        opt_in_query_count = opt_in_query.count()

        # opt in %--------
        total_applications = session.query(Application).count()
        if total_applications != 0:
            opt_in_percentage = (
                session.query(Application)
                .filter(Application.borrower_accepted_at.isnot(None))
                .count()
                / total_applications
            ) * 100
            opt_in_percentage = round(opt_in_percentage, 2)
        else:
            opt_in_percentage = 0

        # opt proportion by sector %--------
        # Calculate total submitted application count
        sectors_count_query = (
            session.query(
                Borrower.sector, func.count(distinct(Application.id)).label("count")
            )
            .join(Application, Borrower.id == Application.borrower_id)
            .filter(
                and_(
                    Application.borrower_accepted_at.isnot(None), Borrower.sector != ""
                )
            )
            .group_by(Borrower.sector)
            .all()
        )
        sectors_count = [
            StatisticData(name=row[0], value=row[1]) for row in sectors_count_query
        ]

        # Count of Declined reasons bars chart
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

        rejected_reasons_count_by_reason = [
            StatisticData(
                name="dont_need_access_credit",
                value=dont_need_access_credit_count,
            ),
            StatisticData(
                name="already_have_acredit", value=already_have_acredit_count
            ),
            StatisticData(
                name="preffer_to_go_to_bank", value=preffer_to_go_to_bank_count
            ),
            StatisticData(
                name="dont_want_access_credit",
                value=dont_want_access_credit_count,
            ),
            StatisticData(name="other", value=other_count),
        ]
        # Bars graph
        fis_choosen_by_msme_query = (
            session.query(Lender.name, func.count(Application.id))
            .join(Lender, Application.lender_id == Lender.id)
            .filter(Application.borrower_submitted_at.isnot(None))
            .group_by(Lender.name)
            .all()
        )
        fis_choosen_by_msme = [
            StatisticData(name=row[0], value=row[1])
            for row in fis_choosen_by_msme_query
        ]

        opt_in_statistics = {
            "opt_in_query_count": opt_in_query_count,
            "opt_in_percentage": opt_in_percentage,
            "sector_statistics": sectors_count,
            "rejected_reasons_count_by_reason": rejected_reasons_count_by_reason,
            "fis_choosen_by_msme": fis_choosen_by_msme,
        }

    except SQLAlchemyError as e:
        raise e

    return opt_in_statistics
