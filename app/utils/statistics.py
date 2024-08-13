from datetime import datetime
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
    return number if number % 1 else int(number)


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

    if application_accepted_count := base_query.filter(col(Application.borrower_submitted_at).isnot(None)).count():
        if lender_id is None:
            column = Application.borrower_accepted_at
        else:
            column = Application.borrower_submitted_at
        proportion_of_submitted_out_of_opt_in = round(
            (application_accepted_count / session.query(Application).filter(col(column).isnot(None)).count()) * 100, 2
        )
    else:
        proportion_of_submitted_out_of_opt_in = 0.0

    general_statistics = {
        "applications_received_count": base_query.filter(col(Application.borrower_submitted_at).isnot(None)).count(),
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
        "average_amount_requested": int(
            _get_base_query(
                session.query(func.avg(Application.amount_requested)),
                start_date,
                end_date,
                lender_id,
            )
            .filter(col(Application.amount_requested).isnot(None))
            .scalar()
            or 0
        ),
        "average_repayment_period": (
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
            .scalar()
            or 0
        ),
        "applications_overdue_count": base_query.filter(col(Application.overdued_at).isnot(None)).count(),
        "average_processing_time": int(
            _get_base_query(
                session.query(func.avg(Application.completed_in_days)),
                start_date,
                end_date,
                lender_id,
            )
            .filter(Application.status == ApplicationStatus.COMPLETED)
            .scalar()
            or 0
        ),
        "proportion_of_submitted_out_of_opt_in": proportion_of_submitted_out_of_opt_in,
    }

    return general_statistics


DEFAULT_MISSING_GENDER = "No definido"


# Group of Stat only for OCP USER (opt in stats)
def get_borrower_opt_in_stats(session: Session) -> dict[str, Any]:
    """
    Get statistics specific to borrower opt-in applications.

    This function retrieves statistics specific opt-in applications. The statistics include the count of
    applications opted-in, the percentage of applications opted-in, statistics related to different sectors, and
    counts of declined reasons.

    :return: A dictionary containing the statistics specific opt-in applications.
    """

    # Reused variables

    woman_values = ("Femenino", "Mujer")
    applications_count = session.query(Application).count()
    accepted_count = session.query(Application).filter(col(Application.borrower_accepted_at).isnot(None)).count()

    # Base queries

    base_declined_applications = session.query(Application).filter(col(Application.borrower_declined_at).isnot(None))

    base_count_by_gender = (
        session.query(
            cast(Award.source_data_contracts["g_nero_representante_legal"], String).label("gender"),
            func.count(Application.id).label("count"),
        )
        .join(Award, Application.award_id == Award.id)
        .join(Borrower, Application.borrower_id == Borrower.id)
        .filter(Borrower.size != BorrowerSize.BIG)
    )

    base_count_by_size = session.query(
        col(Borrower.size).label("size"),
        func.count(Application.id).label("count"),
    ).join(Borrower, Application.borrower_id == Borrower.id)

    base_count_distinct_by_gender = (
        session.query(
            cast(Award.source_data_contracts["g_nero_representante_legal"], String).label("gender"),
            func.count(distinct(Borrower.id)).label("count"),
        )
        .join(Application, Application.borrower_id == Borrower.id)
        .join(Award, Application.award_id == Award.id)
    )

    base_count_distinct_by_size = (
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
            session.query(Borrower.id)
            .join(Award, Award.borrower_id == Borrower.id)
            .join(Application, Application.borrower_id == Borrower.id)
            .filter(col(Application.borrower_accepted_at).isnot(None))
            .group_by(Borrower.id)
            .count()
        ),
        "approved_count": (
            session.query(Application.id)
            .join(Award, Award.id == Application.award_id)
            .filter(col(Application.lender_completed_at).isnot(None))
            .group_by(Application.id)
            .count()
        ),
        "total_credit_disbursed": int(
            session.query(func.sum(Application.disbursed_final_amount))
            .filter(col(Application.lender_completed_at).isnot(None))
            .scalar()
            or 0
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
            session.query(Borrower.id)
            .join(Award, Award.borrower_id == Borrower.id)
            .join(Application, Application.borrower_id == Borrower.id)
            .filter(col(Application.borrower_accepted_at).isnot(None))
            .filter(Borrower.is_msme == true())
            .filter(Award.source_data_contracts["g_nero_representante_legal"].astext.in_(woman_values))
            .group_by(Borrower.id)
            .count()
        ),
        "msme_submitted_count_woman": (
            session.query(Borrower.id)
            .join(Award, Award.borrower_id == Borrower.id)
            .join(Application, Application.borrower_id == Borrower.id)
            .filter(col(Application.borrower_submitted_at).isnot(None))
            .filter(Borrower.size != BorrowerSize.BIG)
            .filter(Award.source_data_contracts["g_nero_representante_legal"].astext.in_(woman_values))
            .group_by(Borrower.id)
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
        "msme_total_credit_disbursed": int(
            session.query(func.sum(Application.disbursed_final_amount))
            .filter(col(Application.lender_completed_at).isnot(None))
            .filter(Borrower.size != BorrowerSize.BIG)
            .join(Borrower, Borrower.id == Application.borrower_id)
            .scalar()
            or 0
        ),
        "approved_count_distinct_micro": (
            session.query(Borrower.id)
            .join(Application, Application.borrower_id == Borrower.id)
            .filter(col(Application.lender_completed_at).isnot(None))
            .filter(Borrower.size == BorrowerSize.MICRO)
            .group_by(Borrower.id)
            .count()
        ),
        "approved_count_distinct_micro_woman": (
            session.query(Borrower.id)
            .join(Application, Application.borrower_id == Borrower.id)
            .join(Award, Award.id == Application.award_id)
            .filter(col(Application.lender_completed_at).isnot(None))
            .filter(Award.source_data_contracts["g_nero_representante_legal"].astext.in_(woman_values))
            .filter(Borrower.size == BorrowerSize.MICRO)
            .group_by(Borrower.id)
            .count()
        ),
        "total_credit_disbursed_micro": int(
            session.query(func.sum(Application.disbursed_final_amount))
            .join(Borrower, Borrower.id == Application.borrower_id)
            .filter(col(Application.lender_completed_at).isnot(None))
            .filter(Borrower.size == BorrowerSize.MICRO)
            .scalar()
            or 0
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
            StatisticData(
                name="dont_need_access_credit",
                value=base_declined_applications.filter(
                    text("(borrower_declined_preferences_data->>'dont_need_access_credit')::boolean is True")
                ).count(),
            ),
            StatisticData(
                name="already_have_acredit",
                value=base_declined_applications.filter(
                    text("(borrower_declined_preferences_data->>'already_have_acredit')::boolean is True")
                ).count(),
            ),
            StatisticData(
                name="preffer_to_go_to_bank",
                value=base_declined_applications.filter(
                    text("(borrower_declined_preferences_data->>'preffer_to_go_to_bank')::boolean is True")
                ).count(),
            ),
            StatisticData(
                name="dont_want_access_credit",
                value=base_declined_applications.filter(
                    text("(borrower_declined_preferences_data->>'dont_want_access_credit')::boolean is True")
                ).count(),
            ),
            StatisticData(
                name="other",
                value=base_declined_applications.filter(
                    text("(borrower_declined_preferences_data->>'other')::boolean is True")
                ).count(),
            ),
        ],
        #
        # Bar graphs by gender and size
        #
        "accepted_count_by_gender": [
            StatisticData(name=row[0].strip('"') if row[0] else DEFAULT_MISSING_GENDER, value=row[1])
            for row in (
                base_count_by_gender.filter(col(Application.borrower_accepted_at).isnot(None)).group_by("gender")
            )
        ],
        "submitted_count_by_gender": [
            StatisticData(name=row[0].strip('"') if row[0] else DEFAULT_MISSING_GENDER, value=row[1])
            for row in (
                base_count_by_gender.filter(col(Application.borrower_submitted_at).isnot(None)).group_by("gender")
            )
        ],
        "approved_count_by_gender": [
            StatisticData(name=row[0].strip('"') if row[0] else DEFAULT_MISSING_GENDER, value=row[1])
            for row in (
                base_count_by_gender.filter(col(Application.lender_completed_at).isnot(None)).group_by("gender")
            )
        ],
        "accepted_count_by_size": [
            StatisticData(name=row[0].strip('"') if row[0] else BorrowerSize.NOT_INFORMED, value=row[1])
            for row in (
                base_count_by_size.filter(col(Application.borrower_accepted_at).isnot(None))
                .filter(Borrower.is_msme == true())
                .group_by("size")
            )
        ],
        "submitted_count_by_size": [
            StatisticData(name=row[0].strip('"') if row[0] else BorrowerSize.NOT_INFORMED, value=row[1])
            for row in (
                base_count_by_size.filter(col(Application.borrower_submitted_at).isnot(None))
                .filter(Borrower.size != BorrowerSize.BIG)
                .group_by("size")
            )
        ],
        "approved_count_by_size": [
            StatisticData(name=row[0].strip('"') if row[0] else BorrowerSize.NOT_INFORMED, value=row[1])
            for row in (
                base_count_by_size.filter(col(Application.lender_completed_at).isnot(None))
                .filter(Borrower.size != BorrowerSize.BIG)
                .group_by("size")
            )
        ],
        #
        # Bars graph by gender and size (distinct)
        #
        "msme_accepted_count_distinct_by_gender": [
            StatisticData(name=row[0].strip('"') if row[0] else DEFAULT_MISSING_GENDER, value=row[1])
            for row in (
                base_count_distinct_by_gender.filter(col(Application.borrower_accepted_at).isnot(None))
                .filter(Borrower.is_msme == true())
                .group_by("gender")
            )
        ],
        "msme_submitted_count_distinct_by_gender": [
            StatisticData(name=row[0].strip('"') if row[0] else DEFAULT_MISSING_GENDER, value=row[1])
            for row in (
                base_count_distinct_by_gender.filter(col(Application.borrower_submitted_at).isnot(None))
                .filter(Borrower.size != BorrowerSize.BIG)
                .group_by("gender")
            )
        ],
        "msme_approved_count_distinct_by_gender": [
            StatisticData(name=row[0].strip('"') if row[0] else DEFAULT_MISSING_GENDER, value=row[1])
            for row in (
                base_count_distinct_by_gender.filter(col(Application.lender_completed_at).isnot(None))
                .filter(Borrower.size != BorrowerSize.BIG)
                .group_by("gender")
            )
        ],
        "accepted_count_distinct_by_size": [
            StatisticData(name=row[0].strip('"') if row[0] else BorrowerSize.NOT_INFORMED, value=row[1])
            for row in (
                base_count_distinct_by_size.filter(col(Application.borrower_accepted_at).isnot(None)).group_by("size")
            )
        ],
        "submitted_count_distinct_by_size": [
            StatisticData(name=row[0].strip('"') if row[0] else BorrowerSize.NOT_INFORMED, value=row[1])
            for row in (
                base_count_distinct_by_size.filter(col(Application.borrower_submitted_at).isnot(None)).group_by("size")
            )
        ],
        "approved_count_distinct_by_size": [
            StatisticData(name=row[0].strip('"') if row[0] else BorrowerSize.NOT_INFORMED, value=row[1])
            for row in (
                base_count_distinct_by_size.filter(col(Application.lender_completed_at).isnot(None)).group_by("size")
            )
        ],
        #
        # Average credit disbursed
        #
        "msme_average_credit_disbursed": _truncate_round(
            (
                session.query(func.avg(Application.disbursed_final_amount))
                .filter(col(Application.lender_completed_at).isnot(None))
                .filter(Borrower.size != BorrowerSize.BIG)
                .join(Borrower, Borrower.id == Application.borrower_id)
                .scalar()
                or 0
            )
        ),
        #
        # Unique number of SMEs who accessed
        #
        "msme_accepted_count_distinct": (
            session.query(func.count(distinct(Borrower.id)))
            .join(Application, Application.borrower_id == Borrower.id)
            .filter(col(Application.borrower_accepted_at).isnot(None))
            .filter(Borrower.is_msme == true())
            .scalar()
            or 0
        ),
        "msme_submitted_count_distinct": (
            session.query(func.count(distinct(Borrower.id)))
            .join(Application, Application.borrower_id == Borrower.id)
            .filter(col(Application.borrower_submitted_at).isnot(None))
            .filter(Borrower.size != BorrowerSize.BIG)
            .scalar()
            or 0
        ),
        "msme_approved_count_distinct": (
            session.query(func.count(distinct(Borrower.id)))
            .join(Application, Application.borrower_id == Borrower.id)
            .filter(col(Application.lender_completed_at).isnot(None))
            .filter(Borrower.size != BorrowerSize.BIG)
            .scalar()
            or 0
        ),
        #
        # Average applications created per day
        #
        "msme_average_applications_per_day": average_applications_per_day,
    }
