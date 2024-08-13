from datetime import datetime
from functools import partial
from typing import Any

from sqlalchemy import Integer, String, cast, distinct, func, select, text, true
from sqlalchemy.orm import Query, Session
from sqlmodel import col

from app.models import (
    Application,
    ApplicationStatus,
    Award,
    Borrower,
    BorrowerSize,
    CreditProduct,
    CreditType,
    Lender,
    StatisticData,
)


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

    if start_date is not None and end_date is not None:
        base_query = session_base.filter(
            col(Application.created_at) >= start_date,
            col(Application.created_at) <= end_date,
        )
    elif start_date is not None:
        base_query = session_base.filter(col(Application.created_at) >= start_date)
    elif end_date is not None:
        base_query = session_base.filter(col(Application.created_at) <= end_date)
    else:
        base_query = session_base

    if lender_id is not None:
        base_query = base_query.filter(Application.lender_id == lender_id)

    return base_query


def _truncate_round(number):
    number = round(number, 2)
    if number % 1:
        return number
    return int(number)


def _scalar_or_zero(query, formatter=None):
    scalar = query.scalar() or 0
    if formatter:
        return formatter(scalar)
    return scalar


def _statistic_data(default, non_null, group, query):
    return [
        StatisticData(name=row[0].strip('"') if row[0] else default, value=row[1])
        for row in query.filter(col(getattr(Application, non_null)).isnot(None)).group_by(group)
    ]


def get_general_statistics(
    session: Session,
    start_date: datetime | str | None = None,
    end_date: datetime | str | None = None,
    lender_id: int | None = None,
) -> dict[str, int | float]:
    """
    Get general statistics about applications based on the provided parameters.

    This function retrieves general statistics about applications based on the provided start_date, end_date, and
    lender_id (if available). The statistics include the count of applications received, approved, rejected, waiting
    for information, in progress, with credit disbursed, proportion of credit disbursed, average amount requested,
    average repayment period, count of overdue applications, average processing time, and proportion of submitted
    applications out of the opt-in applications.

    :param start_date: The start date for filtering applications. (default: None)
    :param end_date: The end date for filtering applications. (default: None)
    :param lender_id: The ID of the lender for filtering applications. (default: None)
    :return: A dictionary containing the general statistics about applications.
    """

    base_query = _get_base_query(session.query(Application), start_date, end_date, lender_id)

    application_received_count = base_query.filter(col(Application.borrower_submitted_at).isnot(None)).count()

    applications_approved_count = base_query.filter(
        col(Application.status).in_(
            [ApplicationStatus.APPROVED, ApplicationStatus.CONTRACT_UPLOADED, ApplicationStatus.COMPLETED]
        )
    ).count()

    applications_with_credit_disbursed_count = base_query.filter(
        Application.status == ApplicationStatus.COMPLETED
    ).count()

    if applications_approved_count and applications_with_credit_disbursed_count:
        proportion_of_disbursed = int(applications_with_credit_disbursed_count / applications_approved_count * 100)
    else:
        proportion_of_disbursed = 0

    if application_received_count:
        if lender_id is None:
            column = Application.borrower_accepted_at
        else:
            column = Application.borrower_submitted_at
        proportion_of_submitted_out_of_opt_in = round(
            (application_received_count / session.query(Application).filter(col(column).isnot(None)).count()) * 100, 2
        )
    else:
        proportion_of_submitted_out_of_opt_in = 0.0

    general_statistics = {
        "applications_received_count": application_received_count,
        "applications_approved_count": applications_approved_count,
        "applications_rejected_count": base_query.filter(Application.status == ApplicationStatus.REJECTED).count(),
        "applications_waiting_for_information_count": base_query.filter(
            Application.status == ApplicationStatus.INFORMATION_REQUESTED
        ).count(),
        "applications_in_progress_count": base_query.filter(
            col(Application.status).in_([ApplicationStatus.STARTED, ApplicationStatus.INFORMATION_REQUESTED])
        ).count(),
        "applications_with_credit_disbursed_count": applications_with_credit_disbursed_count,
        "proportion_of_disbursed": proportion_of_disbursed,
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
            .join(CreditProduct, Application.credit_product_id == CreditProduct.id)
            .filter(
                col(Application.borrower_submitted_at).isnot(None),
                CreditProduct.type == CreditType.LOAN,
            )
        ),
        "applications_overdue_count": base_query.filter(col(Application.overdued_at).isnot(None)).count(),
        "average_processing_time": _scalar_or_zero(
            _get_base_query(
                session.query(func.avg(Application.completed_in_days)), start_date, end_date, lender_id
            ).filter(Application.status == ApplicationStatus.COMPLETED),
            formatter=int,
        ),
        "proportion_of_submitted_out_of_opt_in": proportion_of_submitted_out_of_opt_in,
    }

    return general_statistics


# Group of Stat only for OCP USER (opt in stats)
def get_borrower_opt_in_stats(session: Session) -> dict[str, Any]:
    """
    Get statistics specific to borrower opt-in applications.

    This function retrieves statistics specific opt-in applications. The statistics include the count of
    applications opted-in, the percentage of applications opted-in, statistics related to different sectors, and
    counts of declined reasons.

    :return: A dictionary containing the statistics specific opt-in applications.
    """

    def _rejected_reason(reason):
        return StatisticData(
            name=reason,
            value=base_declined_applications.filter(
                text(f"(borrower_declined_preferences_data->>'{reason}')::boolean is True")
            ).count(),
        )

    # Reused variables

    woman_values = ("Femenino", "Mujer")
    applications_count = session.query(Application).count()
    accepted_count = session.query(Application).filter(col(Application.borrower_accepted_at).isnot(None)).count()

    statistic_gender = partial(_statistic_data, group="gender", default="No definido")
    statistic_size = partial(_statistic_data, group="size", default=BorrowerSize.NOT_INFORMED)

    # Base queries

    base_borrower_group = (
        session.query(Borrower.id).join(Application, Application.borrower_id == Borrower.id).group_by(Borrower.id)
    )
    base_borrower_group_with_award = base_borrower_group.join(Award, Award.borrower_id == Borrower.id)

    base_declined_applications = session.query(Application).filter(col(Application.borrower_declined_at).isnot(None))

    base_count_gender = (
        session.query(
            cast(Award.source_data_contracts["g_nero_representante_legal"], String).label("gender"),
            func.count(Application.id).label("count"),
        )
        .join(Award, Application.award_id == Award.id)
        .join(Borrower, Application.borrower_id == Borrower.id)
        .filter(Borrower.size != BorrowerSize.BIG)
    )

    base_count_size = session.query(
        col(Borrower.size).label("size"),
        func.count(Application.id).label("count"),
    ).join(Borrower, Application.borrower_id == Borrower.id)

    base_distinct_gender = (
        session.query(
            cast(Award.source_data_contracts["g_nero_representante_legal"], String).label("gender"),
            func.count(distinct(Borrower.id)).label("count"),
        )
        .join(Application, Application.borrower_id == Borrower.id)
        .join(Award, Application.award_id == Award.id)
    )

    base_distinct_size = (
        session.query(
            col(Borrower.size).label("size"),
            func.count(distinct(Borrower.id)).label("count"),
        )
        .join(Application, Application.borrower_id == Borrower.id)
        .join(Award, Application.award_id == Award.id)
    )

    # Complex logic

    if daily_counts := session.query(
        select(func.date_trunc("day", Application.created_at).label("day"), func.count().label("daily_count"))
        .group_by(func.date_trunc("day", Application.created_at))
        .alias("daily_counts")
    ).all():
        average_applications_per_day = _truncate_round(
            sum(row.daily_count for row in daily_counts) / len(daily_counts)
        )
    else:
        average_applications_per_day = 0

    return {
        #
        # General statistics - all suppliers
        #
        "applications_created": applications_count,
        "accepted_count": accepted_count,
        "accepted_percentage": round((accepted_count / applications_count * 100), 2) if applications_count else 0,
        "unique_businesses_contacted_by_credere": session.query(Borrower).count(),
        "accepted_count_unique": (
            base_borrower_group_with_award.filter(col(Application.borrower_accepted_at).isnot(None)).count()
        ),
        "approved_count": (
            session.query(Application.id)
            .join(Award, Award.id == Application.award_id)
            .filter(col(Application.lender_completed_at).isnot(None))
            .group_by(Application.id)
            .count()
        ),
        "total_credit_disbursed": _scalar_or_zero(
            session.query(func.sum(Application.disbursed_final_amount)).filter(
                col(Application.lender_completed_at).isnot(None)
            ),
            formatter=int,
        ),
        #
        # Bar graphs
        #
        "fis_chosen_by_supplier": [
            StatisticData(name=row[0], value=row[1])
            for row in (
                session.query(Lender.name, func.count(Application.id))
                .join(Lender, Application.lender_id == Lender.id)
                .filter(col(Application.borrower_submitted_at).isnot(None))
                .group_by(Lender.name)
            )
        ],
        "msme_accepted_count_woman": (
            base_borrower_group_with_award.filter(col(Application.borrower_accepted_at).isnot(None))
            .filter(Borrower.is_msme == true())
            .filter(Award.source_data_contracts["g_nero_representante_legal"].astext.in_(woman_values))
            .count()
        ),
        "msme_submitted_count_woman": (
            base_borrower_group_with_award.filter(col(Application.borrower_submitted_at).isnot(None))
            .filter(Borrower.size != BorrowerSize.BIG)
            .filter(Award.source_data_contracts["g_nero_representante_legal"].astext.in_(woman_values))
            .count()
        ),
        "msme_approved_count_woman": (
            session.query(Application.id)
            .join(Award, Award.id == Application.award_id)
            .join(Borrower, Application.borrower_id == Borrower.id)
            .filter(col(Application.lender_completed_at).isnot(None))
            .filter(Borrower.size != BorrowerSize.BIG)
            .filter(Award.source_data_contracts["g_nero_representante_legal"].astext.in_(woman_values))
            .group_by(Application.id)
            .count()
        ),
        "msme_approved_count": (
            session.query(Application.id)
            .join(Borrower, Borrower.id == Application.borrower_id)
            .filter(col(Application.lender_completed_at).isnot(None))
            .filter(Borrower.size != BorrowerSize.BIG)
            .count()
        ),
        "msme_total_credit_disbursed": _scalar_or_zero(
            session.query(func.sum(Application.disbursed_final_amount))
            .join(Borrower, Borrower.id == Application.borrower_id)
            .filter(col(Application.lender_completed_at).isnot(None))
            .filter(Borrower.size != BorrowerSize.BIG),
            formatter=int,
        ),
        "approved_count_distinct_micro": (
            base_borrower_group.filter(col(Application.lender_completed_at).isnot(None))
            .filter(Borrower.size == BorrowerSize.MICRO)
            .count()
        ),
        "approved_count_distinct_micro_woman": (
            base_borrower_group.join(Award, Award.id == Application.award_id)
            .filter(col(Application.lender_completed_at).isnot(None))
            .filter(Award.source_data_contracts["g_nero_representante_legal"].astext.in_(woman_values))
            .filter(Borrower.size == BorrowerSize.MICRO)
            .count()
        ),
        "total_credit_disbursed_micro": _scalar_or_zero(
            session.query(func.sum(Application.disbursed_final_amount))
            .join(Borrower, Borrower.id == Application.borrower_id)
            .filter(col(Application.lender_completed_at).isnot(None))
            .filter(Borrower.size == BorrowerSize.MICRO),
            formatter=int,
        ),
        #
        # MSMEs statistics
        #
        "unique_smes_contacted_by_credere": session.query(Borrower).filter(col(Borrower.is_msme).is_(True)).count(),
        "sector_statistics": [
            StatisticData(name=row[0], value=row[1])
            for row in (
                session.query(Borrower.sector, func.count(distinct(Application.id)).label("count"))
                .join(Application, Borrower.id == Application.borrower_id)
                .filter(
                    col(Application.borrower_accepted_at).isnot(None),
                    Borrower.sector != "",
                    Borrower.size != BorrowerSize.BIG,
                )
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
            _rejected_reason("other"),
        ],
        #
        # Bar graphs by gender and size
        #
        "accepted_count_by_gender": statistic_gender(query=base_count_gender, non_null="borrower_accepted_at"),
        "submitted_count_by_gender": statistic_gender(query=base_count_gender, non_null="borrower_submitted_at"),
        "approved_count_by_gender": statistic_gender(query=base_count_gender, non_null="lender_completed_at"),
        "accepted_count_by_size": statistic_size(
            query=base_count_size.filter(Borrower.is_msme == true()), non_null="borrower_accepted_at"
        ),
        "submitted_count_by_size": statistic_size(
            query=base_count_size.filter(Borrower.size != BorrowerSize.BIG), non_null="borrower_submitted_at"
        ),
        "approved_count_by_size": statistic_size(
            query=base_count_size.filter(Borrower.size != BorrowerSize.BIG), non_null="lender_completed_at"
        ),
        #
        # Bars graph by gender and size (distinct)
        #
        "msme_accepted_count_distinct_by_gender": statistic_gender(
            query=base_distinct_gender.filter(Borrower.is_msme == true()), non_null="borrower_accepted_at"
        ),
        "msme_submitted_count_distinct_by_gender": statistic_gender(
            query=base_distinct_gender.filter(Borrower.size != BorrowerSize.BIG), non_null="borrower_submitted_at"
        ),
        "msme_approved_count_distinct_by_gender": statistic_gender(
            query=base_distinct_gender.filter(Borrower.size != BorrowerSize.BIG), non_null="lender_completed_at"
        ),
        "accepted_count_distinct_by_size": statistic_size(query=base_distinct_size, non_null="borrower_accepted_at"),
        "submitted_count_distinct_by_size": statistic_size(query=base_distinct_size, non_null="borrower_submitted_at"),
        "approved_count_distinct_by_size": statistic_size(query=base_distinct_size, non_null="lender_completed_at"),
        #
        # Average credit disbursed
        #
        "msme_average_credit_disbursed": _scalar_or_zero(
            session.query(func.avg(Application.disbursed_final_amount))
            .join(Borrower, Borrower.id == Application.borrower_id)
            .filter(col(Application.lender_completed_at).isnot(None))
            .filter(Borrower.size != BorrowerSize.BIG),
            formatter=_truncate_round,
        ),
        #
        # Unique number of SMEs who accessed
        #
        "msme_accepted_count_distinct": _scalar_or_zero(
            session.query(func.count(distinct(Borrower.id)))
            .join(Application, Application.borrower_id == Borrower.id)
            .filter(col(Application.borrower_accepted_at).isnot(None))
            .filter(Borrower.is_msme == true())
        ),
        "msme_submitted_count_distinct": _scalar_or_zero(
            session.query(func.count(distinct(Borrower.id)))
            .join(Application, Application.borrower_id == Borrower.id)
            .filter(col(Application.borrower_submitted_at).isnot(None))
            .filter(Borrower.size != BorrowerSize.BIG)
        ),
        "msme_approved_count_distinct": _scalar_or_zero(
            session.query(func.count(distinct(Borrower.id)))
            .join(Application, Application.borrower_id == Borrower.id)
            .filter(col(Application.lender_completed_at).isnot(None))
            .filter(Borrower.size != BorrowerSize.BIG)
        ),
        #
        # Average applications created per day
        #
        "msme_average_applications_per_day": average_applications_per_day,
    }
