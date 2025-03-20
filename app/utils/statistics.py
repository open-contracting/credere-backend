from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy import Integer, distinct, func, text, true
from sqlalchemy.orm import Query, Session
from sqlmodel import col

from app.models import Application, ApplicationStatus, Award, Borrower, BorrowerSize, CreditProduct, CreditType, Lender
from app.serializers import StatisticData


def _get_base_query(
    session_base: "Query[Application]",
    start_date: datetime | str | None,
    end_date: datetime | str | None,
    lender_id: int | None,
) -> "Query[Application]":
    """
    Create the base query for filtering applications based on the provided start_date, end_date, and lender_id.

    This function creates the base query for filtering applications from the database. The filtering is based on
    the provided start_date, end_date, and lender_id (if available).

    :param session_base: The base query representing the Application model.
    :param start_date: The start date for filtering applications. (default: None)
    :param end_date: The end date for filtering applications. (default: None)
    :param lender_id: The ID of the lender for filtering applications. (default: None)
    :return: The base query for filtering applications.
    """
    base_query = session_base

    if start_date:
        base_query = base_query.filter(col(Application.created_at) >= start_date)
    if end_date:
        base_query = base_query.filter(col(Application.created_at) <= end_date)

    if lender_id:
        base_query = base_query.filter(Application.lender_id == lender_id)

    return base_query


def _truncate_round(number: float) -> int | float:
    number = round(number, 2)
    if number % 1:
        return number
    return int(number)


def _scalar_or_zero(
    query: Query[Application] | Query[Borrower], formatter: Callable[[float], int | float] | None = None
) -> int | float:
    scalar = query.scalar() or 0
    if formatter:
        return formatter(scalar)
    return scalar


def get_general_statistics(
    session: Session,
    start_date: datetime | str | None = None,
    end_date: datetime | str | None = None,
    lender_id: int | None = None,
) -> dict[str, int | float]:
    """
    Get general statistics about applications based on the provided parameters.

    This function retrieves general statistics about applications based on the provided start_date, end_date, and
    lender_id (if available).

    :param start_date: The start date for filtering applications. (default: None)
    :param end_date: The end date for filtering applications. (default: None)
    :param lender_id: The ID of the lender for filtering applications. (default: None)
    :return: A dictionary containing the general statistics about applications.
    """
    base_query = _get_base_query(session.query(Application.id), start_date, end_date, lender_id)

    application_received_count = base_query.filter(col(Application.borrower_submitted_at).isnot(None)).count()

    applications_with_credit_disbursed_count = base_query.filter(
        Application.status == ApplicationStatus.APPROVED
    ).count()

    column = Application.borrower_accepted_at if lender_id is None else Application.borrower_submitted_at
    application_submitted_count = session.query(Application.id).filter(col(column).isnot(None)).count()
    if application_submitted_count:
        proportion_of_submitted_out_of_opt_in = round(
            (application_received_count / application_submitted_count) * 100, 2
        )
    else:
        proportion_of_submitted_out_of_opt_in = 0.0

    return {
        "applications_received_count": application_received_count,
        "applications_rejected_count": base_query.filter(Application.status == ApplicationStatus.REJECTED).count(),
        "applications_waiting_for_information_count": base_query.filter(
            Application.status == ApplicationStatus.INFORMATION_REQUESTED
        ).count(),
        "applications_in_progress_count": base_query.filter(
            col(Application.status).in_((ApplicationStatus.STARTED, ApplicationStatus.INFORMATION_REQUESTED))
        ).count(),
        "applications_with_credit_disbursed_count": applications_with_credit_disbursed_count,
        "average_amount_requested": _scalar_or_zero(
            _get_base_query(
                session.query(func.avg(Application.amount_requested)), start_date, end_date, lender_id
            ).filter(col(Application.amount_requested).isnot(None)),
            formatter=int,
        ),
        "average_repayment_period": _scalar_or_zero(
            _get_base_query(
                session.query(
                    func.avg(col(Application.repayment_years) * 12 + col(Application.repayment_months)).cast(Integer)
                ),
                start_date,
                end_date,
                lender_id,
            )
            .join(CreditProduct, CreditProduct.id == Application.credit_product_id)
            .filter(
                col(Application.borrower_submitted_at).isnot(None),
                CreditProduct.type == CreditType.LOAN,
            )
        ),
        "applications_overdue_count": base_query.filter(col(Application.overdued_at).isnot(None)).count(),
        "average_processing_time": _scalar_or_zero(
            _get_base_query(
                session.query(func.avg(Application.completed_in_days)), start_date, end_date, lender_id
            ).filter(col(Application.status).in_((ApplicationStatus.APPROVED, ApplicationStatus.REJECTED))),
            formatter=int,
        ),
        "proportion_of_submitted_out_of_opt_in": proportion_of_submitted_out_of_opt_in,
    }


# Group of Stat only for OCP USER (opt in stats)
def get_borrower_opt_in_stats(session: Session) -> dict[str, Any]:
    """
    Get statistics specific to borrower opt-in applications.

    This function retrieves statistics specific opt-in applications. The statistics include the count of
    applications opted-in, the percentage of applications opted-in, statistics related to different sectors, and
    counts of declined reasons.

    :return: A dictionary containing the statistics specific opt-in applications.
    """

    def _rejected_reason(reason: str) -> StatisticData:
        return StatisticData(
            name=reason,
            value=base_application.filter(declined)
            .filter(text(f"(borrower_declined_preferences_data->>'{reason}')::boolean is True"))
            .count(),
        )

    # Filters

    # When filtering by dates, remember to query or join Application.
    accepted = col(Application.borrower_accepted_at).isnot(None)
    declined = col(Application.borrower_declined_at).isnot(None)
    submitted = col(Application.borrower_submitted_at).isnot(None)
    approved = col(Application.lender_approved_at).isnot(None)
    # When filtering by size, remember to query or join Borrower.
    msme_from_source = Borrower.is_msme == true()
    msme_from_borrower = Borrower.size != BorrowerSize.BIG
    micro = Borrower.size == BorrowerSize.MICRO
    # When filtering by woman-owned, remember to join Award.
    woman_owned = Award.source_data_contracts["g_nero_representante_legal"].astext.in_(("Femenino", "Mujer"))

    # Base queries

    base_application = session.query(Application.id)

    base_borrower_distinct = session.query(func.count(distinct(Borrower.id))).join(Application)
    base_borrower_group = session.query(Borrower.id).join(Application).group_by(Borrower.id)
    base_borrower_group_with_award = base_borrower_group.join(Award, Award.id == Application.award_id)

    # Reused variables

    applications_count = base_application.count()
    accepted_count = base_application.filter(accepted).count()

    return {
        #
        # General statistics - all suppliers
        #
        "applications_created": applications_count,
        "accepted_count": accepted_count,
        "accepted_percentage": round((accepted_count / applications_count * 100), 2) if applications_count else 0,
        "unique_businesses_contacted_by_credere": session.query(Borrower.id).count(),
        "accepted_count_unique": base_borrower_group.filter(accepted).count(),
        "approved_count": base_application.filter(approved).count(),
        "total_credit_disbursed": _scalar_or_zero(
            session.query(func.sum(Application.disbursed_final_amount)).filter(approved),
            formatter=int,
        ),
        #
        # Bar graphs
        #
        "fis_chosen_by_supplier": [
            StatisticData(name=name, value=value)
            for name, value in (
                session.query(Lender.name, func.count(Application.id))
                .join(Lender)
                .filter(submitted)
                .group_by(Lender.name)
            )
        ],
        # "Unique women-led SMEs that use Credere to access credit options"
        "msme_accepted_count_woman": (
            base_borrower_group_with_award.filter(accepted, msme_from_source, woman_owned).count()
        ),
        # "Number of women-led SMEs that submit a credit application through Credere"
        "msme_submitted_count_woman": (
            base_borrower_group_with_award.filter(submitted, msme_from_borrower, woman_owned).count()
        ),
        # This query matches msme_approved_count, instead of msme_accepted_count_woman or msme_submitted_count_woman,
        # because it counts applications, not borrowers. The variable name is similar but the semantics are different.
        # "Number of women-led SMEs credit applications approved"
        "msme_approved_count_woman": (
            session.query(Application.id)
            .join(Borrower)
            .join(Award, Award.id == Application.award_id)
            .filter(approved, msme_from_borrower, woman_owned)
            .group_by(Application.id)
            .count()
        ),
        # "Number of SMEs applications approved"
        "msme_approved_count": (
            session.query(Application.id).join(Borrower).filter(approved, msme_from_borrower).count()
        ),
        "msme_total_credit_disbursed": _scalar_or_zero(
            session.query(func.sum(Application.disbursed_final_amount))
            .join(Borrower)
            .filter(approved, msme_from_borrower),
            formatter=int,
        ),
        "approved_count_distinct_micro": base_borrower_group.filter(approved, micro).count(),
        "approved_count_distinct_micro_woman": (
            base_borrower_group_with_award.filter(approved, micro, woman_owned).count()
        ),
        "total_credit_disbursed_micro": _scalar_or_zero(
            session.query(func.sum(Application.disbursed_final_amount)).join(Borrower).filter(approved, micro),
            formatter=int,
        ),
        #
        # MSMEs statistics
        #
        "unique_smes_contacted_by_credere": session.query(Borrower.id).filter(col(Borrower.is_msme).is_(True)).count(),
        "sector_statistics": [
            StatisticData(name=name, value=value)
            for name, value in (
                session.query(Borrower.sector, func.count(distinct(Application.id)).label("count"))
                .join(Application)
                .filter(accepted, msme_from_source, Borrower.sector != "")
                .group_by(Borrower.sector)
            )
        ],
        #
        # Count of Declined reasons bars chart
        #
        "rejected_reasons_count_by_reason": [
            _rejected_reason("dont_need_access_credit"),
            _rejected_reason("already_have_acredit"),
            _rejected_reason("preffer_to_go_to_bank"),
            _rejected_reason("dont_want_access_credit"),
            _rejected_reason("suspicious_email"),
            _rejected_reason("other"),
        ],
        #
        # Average credit disbursed
        #
        "msme_average_credit_disbursed": _scalar_or_zero(
            session.query(func.avg(Application.disbursed_final_amount))
            .join(Borrower)
            .filter(approved, msme_from_borrower),
            formatter=_truncate_round,
        ),
        #
        # Unique number of SMEs who accessed
        #
        "msme_accepted_count_distinct": _scalar_or_zero(base_borrower_distinct.filter(accepted, msme_from_source)),
        "msme_submitted_count_distinct": _scalar_or_zero(base_borrower_distinct.filter(submitted, msme_from_borrower)),
        "msme_approved_count_distinct": _scalar_or_zero(base_borrower_distinct.filter(approved, msme_from_borrower)),
    }
