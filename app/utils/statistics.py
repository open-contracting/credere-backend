from contextlib import contextmanager
from datetime import datetime
from typing import Any, Callable, Generator

from sqlalchemy import Date, Integer, String, cast, distinct, func, select, text
from sqlalchemy.orm import Query, Session
from sqlmodel import col

from app.db import get_db, rollback_on_error
from app.models import (
    Application,
    ApplicationStatus,
    Award,
    Borrower,
    BorrowerSize,
    CreditProduct,
    CreditType,
    Lender,
    Statistic,
    StatisticData,
    StatisticType,
)

keys_to_serialize = [
    "sector_statistics",
    "rejected_reasons_count_by_reason",
    "fis_chosen_by_msme",
    "accepted_count_by_gender",
    "submitted_count_by_gender",
    "approved_count_by_gender",
    "accepted_count_by_size",
    "submitted_count_by_size",
    "approved_count_by_size",
    "accepted_count_distinct_by_gender",
    "submitted_count_distinct_by_gender",
    "approved_count_distinct_by_gender",
    "accepted_count_distinct_by_size",
    "submitted_count_distinct_by_size",
    "approved_count_distinct_by_size",
]


# A background task.
def update_statistics(db_provider: Callable[[], Generator[Session, None, None]] = get_db) -> None:
    """
    Update and store various statistics related to applications and lenders in the database.

    This function retrieves and logs different types of statistics related to applications
    and lenders. It uses the `get_general_statistics` and `get_msme_opt_in_stats` functions
    to fetch the respective statistics.

    After fetching the general statistics, this function attempts to store them in the database
    as an instance of the `Statistic` model. The statistics are stored with the type set to
    `StatisticType.APPLICATION_KPIS`. The `Statistic` model contains a JSON field to store
    the actual statistical data.

    Example usage:
    >>> update_statistics()
    """

    with contextmanager(db_provider)() as session:
        with rollback_on_error(session):
            # Get general Kpis
            statistic_kpis = get_general_statistics(session, None, None, None)

            Statistic.create_or_update(
                session,
                [
                    cast(Statistic.created_at, Date) == datetime.today().date(),
                    Statistic.type == StatisticType.APPLICATION_KPIS,
                ],
                type=StatisticType.APPLICATION_KPIS,
                data=statistic_kpis,
            )

            # Get Opt in statistics
            statistics_msme_opt_in = get_msme_opt_in_stats(session)
            for key in keys_to_serialize:
                statistics_msme_opt_in[key] = [data.model_dump() for data in statistics_msme_opt_in[key]]

            Statistic.create_or_update(
                session,
                [
                    cast(Statistic.created_at, Date) == datetime.today().date(),
                    Statistic.type == StatisticType.MSME_OPT_IN_STATISTICS,
                ],
                type=StatisticType.MSME_OPT_IN_STATISTICS,
                data=statistics_msme_opt_in,
            )

            # Get general Kpis for every lender
            lender_ids = [id[0] for id in session.query(Lender.id).all()]
            for lender_id in lender_ids:
                # Get statistics for each lender
                statistic_kpis = get_general_statistics(session, None, None, lender_id)

                Statistic.create_or_update(
                    session,
                    [
                        cast(Statistic.created_at, Date) == datetime.today().date(),
                        Statistic.type == StatisticType.APPLICATION_KPIS,
                        Statistic.lender_id == lender_id,
                    ],
                    type=StatisticType.APPLICATION_KPIS,
                    data=statistic_kpis,
                    lender_id=lender_id,
                )

            session.commit()


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

    # received
    applications_received_query = base_query.filter(col(Application.borrower_submitted_at).isnot(None))
    applications_received_count = applications_received_query.count()

    # approved
    applications_approved_query = base_query.filter(
        col(Application.status).in_(
            [ApplicationStatus.APPROVED, ApplicationStatus.CONTRACT_UPLOADED, ApplicationStatus.COMPLETED]
        )
    )
    applications_approved_count = applications_approved_query.count()

    # rejected
    applications_rejected_query = base_query.filter(Application.status == ApplicationStatus.REJECTED)
    applications_rejected_count = applications_rejected_query.count()

    # waiting
    applications_waiting_query = base_query.filter(Application.status == ApplicationStatus.INFORMATION_REQUESTED)
    applications_waiting_count = applications_waiting_query.count()

    # in progress
    applications_in_progress_query = base_query.filter(
        col(Application.status).in_([ApplicationStatus.STARTED, ApplicationStatus.INFORMATION_REQUESTED])
    )
    applications_in_progress_count = applications_in_progress_query.count()

    # credit disbursed
    applications_with_credit_disbursed = base_query.filter(Application.status == ApplicationStatus.COMPLETED)
    applications_with_credit_disbursed_count = applications_with_credit_disbursed.count()

    # credit disbursed %
    if applications_approved_count == 0 or applications_with_credit_disbursed_count == 0:
        proportion_of_disbursed = 0
    else:
        proportion_of_disbursed = int(applications_with_credit_disbursed_count / applications_approved_count * 100)

    # Average amount requested
    average_amount_requested_query = _get_base_query(
        session.query(func.avg(Application.amount_requested)),
        start_date,
        end_date,
        lender_id,
    ).filter(
        col(Application.amount_requested).isnot(None),
    )

    average_amount_requested_result = average_amount_requested_query.scalar()
    average_amount_requested = (
        int(average_amount_requested_result) if average_amount_requested_result is not None else 0
    )

    # Average Repayment Period
    average_repayment_period_query = (
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
    )

    average_repayment_period = average_repayment_period_query.scalar() or 0

    # Overdue Application
    applications_overdue_query = base_query.filter(col(Application.overdued_at).isnot(None))
    applications_overdue_count = applications_overdue_query.count()

    # average time to process application
    average_processing_time_query = _get_base_query(
        session.query(func.avg(Application.completed_in_days)),
        start_date,
        end_date,
        lender_id,
    ).filter(
        Application.status == ApplicationStatus.COMPLETED,
    )

    average_processing_time_result = average_processing_time_query.scalar()
    average_processing_time = int(average_processing_time_result) if average_processing_time_result is not None else 0
    #  get_proportion_of_submited_out_of_opt_in
    application_accepted_query = base_query.filter(col(Application.borrower_submitted_at).isnot(None)).count()

    if lender_id is not None:
        application_divisor = (
            session.query(Application).filter(col(Application.borrower_submitted_at).isnot(None)).count()
        )
    else:
        application_divisor = (
            session.query(Application).filter(col(Application.borrower_accepted_at).isnot(None)).count()
        )

    # Calculate the proportion
    if application_accepted_query == 0:
        proportion_of_submitted_out_of_opt_in = 0.0
    else:
        proportion_of_submitted_out_of_opt_in = round((application_accepted_query / application_divisor) * 100, 2)

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

    return general_statistics


DEFAULT_MISSING_GENDER = "No definido"


# Group of Stat only for OCP USER (msme opt in stats)
def get_msme_opt_in_stats(session: Session) -> dict[str, Any]:
    """
    Get statistics specific to MSME opt-in applications.

    This function retrieves statistics specific to MSME opt-in applications. The statistics include the count of
    applications opted-in, the percentage of applications opted-in, statistics related to different sectors, and
    counts of declined reasons.

    :return: A dictionary containing the statistics specific to MSME opt-in applications.
    """

    WOMAN_VALUES = ("Femenino", "Mujer")

    unique_smes_contacted_by_credere = session.query(Borrower).count()

    accepted_query = session.query(Application).filter(col(Application.borrower_accepted_at).isnot(None))
    accepted_query_count = accepted_query.count()

    total_applications = session.query(Application).count()
    accepted_percentage = round(((accepted_query_count / total_applications) * 100), 2) if total_applications else 0

    sectors_count_query = (
        session.query(Borrower.sector, func.count(distinct(Application.id)).label("count"))
        .join(Application, Borrower.id == Application.borrower_id)
        .filter(
            col(Application.borrower_accepted_at).isnot(None),
            Borrower.sector != "",
        )
        .group_by(Borrower.sector)
        .all()
    )
    sectors_count = [StatisticData(name=row[0], value=row[1]) for row in sectors_count_query]

    # Count of Declined reasons bars chart
    declined_applications = session.query(Application).filter(col(Application.borrower_declined_at).isnot(None))

    # Count occurrences for each case
    dont_need_access_credit_count = declined_applications.filter(
        text("(borrower_declined_preferences_data->>'dont_need_access_credit')::boolean is True")
    ).count()

    already_have_acredit_count = declined_applications.filter(
        text("(borrower_declined_preferences_data->>'already_have_acredit')::boolean is True")
    ).count()

    preffer_to_go_to_bank_count = declined_applications.filter(
        text("(borrower_declined_preferences_data->>'preffer_to_go_to_bank')::boolean is True")
    ).count()

    dont_want_access_credit_count = declined_applications.filter(
        text("(borrower_declined_preferences_data->>'dont_want_access_credit')::boolean is True")
    ).count()

    other_count = declined_applications.filter(
        text("(borrower_declined_preferences_data->>'other')::boolean is True")
    ).count()

    rejected_reasons_count_by_reason = [
        StatisticData(
            name="dont_need_access_credit",
            value=dont_need_access_credit_count,
        ),
        StatisticData(name="already_have_acredit", value=already_have_acredit_count),
        StatisticData(name="preffer_to_go_to_bank", value=preffer_to_go_to_bank_count),
        StatisticData(
            name="dont_want_access_credit",
            value=dont_want_access_credit_count,
        ),
        StatisticData(name="other", value=other_count),
    ]
    # Bars graph
    fis_chosen_by_msme_query = (
        session.query(Lender.name, func.count(Application.id))
        .join(Lender, Application.lender_id == Lender.id)
        .filter(col(Application.borrower_submitted_at).isnot(None))
        .group_by(Lender.name)
        .all()
    )
    fis_chosen_by_msme = [StatisticData(name=row[0], value=row[1]) for row in fis_chosen_by_msme_query]

    accepted_count_woman_unique = (
        session.query(Borrower.id)
        .join(Award, Award.borrower_id == Borrower.id)
        .join(Application, Application.borrower_id == Borrower.id)
        .filter(Application.borrower_accepted_at.isnot(None))
        .filter(Award.source_data_contracts["g_nero_representante_legal"].astext.in_(WOMAN_VALUES))
        .group_by(Borrower.id)
        .count()
    )

    approved_count_woman = (
        session.query(Application.id)
        .join(Award, Award.id == Application.award_id)
        .filter(Application.lender_completed_at.isnot(None))
        .filter(Award.source_data_contracts["g_nero_representante_legal"].astext.in_(WOMAN_VALUES))
        .group_by(Application.id)
        .count()
    )

    base_count_by_gender_query = session.query(
        cast(Award.source_data_contracts["g_nero_representante_legal"], String).label("gender"),
        func.count(Application.id).label("count"),
    ).join(Award, Application.award_id == Award.id)

    # Bars graph by gender and size
    accepted_count_by_gender_query = (
        base_count_by_gender_query.filter(Application.borrower_accepted_at.isnot(None)).group_by("gender").all()
    )

    accepted_count_by_gender = [
        StatisticData(name=row[0].strip('"') if row[0] else DEFAULT_MISSING_GENDER, value=row[1])
        for row in accepted_count_by_gender_query
    ]

    submitted_count_by_gender_query = (
        base_count_by_gender_query.filter(Application.borrower_submitted_at.isnot(None)).group_by("gender").all()
    )

    submitted_count_by_gender = [
        StatisticData(name=row[0].strip('"') if row[0] else DEFAULT_MISSING_GENDER, value=row[1])
        for row in submitted_count_by_gender_query
    ]

    approved_count = session.query(Application.id).filter(Application.lender_completed_at.isnot(None)).count()

    approved_count_by_gender_query = (
        base_count_by_gender_query.filter(Application.lender_completed_at.isnot(None)).group_by("gender").all()
    )

    approved_count_by_gender = [
        StatisticData(name=row[0].strip('"') if row[0] else DEFAULT_MISSING_GENDER, value=row[1])
        for row in approved_count_by_gender_query
    ]

    base_count_by_size_query = session.query(
        Borrower.size.label("size"),
        func.count(Application.id).label("count"),
    ).join(Borrower, Application.borrower_id == Borrower.id)

    accepted_count_by_size_query = (
        base_count_by_size_query.filter(Application.borrower_accepted_at.isnot(None)).group_by("size").all()
    )

    accepted_count_by_size = [
        StatisticData(name=row[0].strip('"') if row[0] else BorrowerSize.NOT_INFORMED, value=row[1])
        for row in accepted_count_by_size_query
    ]

    submitted_count_by_size_query = (
        base_count_by_size_query.filter(Application.borrower_submitted_at.isnot(None)).group_by("size").all()
    )

    submitted_count_by_size = [
        StatisticData(name=row[0].strip('"') if row[0] else BorrowerSize.NOT_INFORMED, value=row[1])
        for row in submitted_count_by_size_query
    ]

    approved_count_by_size_query = (
        base_count_by_size_query.filter(Application.lender_completed_at.isnot(None)).group_by("size").all()
    )

    approved_count_by_size = [
        StatisticData(name=row[0].strip('"') if row[0] else BorrowerSize.NOT_INFORMED, value=row[1])
        for row in approved_count_by_size_query
    ]

    # Bars graph by gender and size (distinct)
    base_count_distinct_by_gender_query = (
        session.query(
            cast(Award.source_data_contracts["g_nero_representante_legal"], String).label("gender"),
            func.count(distinct(Borrower.id)).label("count"),
        )
        .join(Application, Application.borrower_id == Borrower.id)
        .join(Award, Application.award_id == Award.id)
    )

    accepted_count_distinct_by_gender_query = (
        base_count_distinct_by_gender_query.filter(Application.borrower_accepted_at.isnot(None))
        .group_by("gender")
        .all()
    )

    accepted_count_distinct_by_gender = [
        StatisticData(name=row[0].strip('"') if row[0] else DEFAULT_MISSING_GENDER, value=row[1])
        for row in accepted_count_distinct_by_gender_query
    ]

    submitted_count_distinct_by_gender_query = (
        base_count_distinct_by_gender_query.filter(Application.borrower_submitted_at.isnot(None))
        .group_by("gender")
        .all()
    )

    submitted_count_distinct_by_gender = [
        StatisticData(name=row[0].strip('"') if row[0] else DEFAULT_MISSING_GENDER, value=row[1])
        for row in submitted_count_distinct_by_gender_query
    ]

    approved_count_distinct_by_gender_query = (
        base_count_distinct_by_gender_query.filter(Application.lender_completed_at.isnot(None))
        .group_by("gender")
        .all()
    )

    approved_count_distinct_by_gender = [
        StatisticData(name=row[0].strip('"') if row[0] else DEFAULT_MISSING_GENDER, value=row[1])
        for row in approved_count_distinct_by_gender_query
    ]

    base_count_distinct_by_size_query = (
        session.query(
            Borrower.size.label("size"),
            func.count(distinct(Borrower.id)).label("count"),
        )
        .join(Application, Application.borrower_id == Borrower.id)
        .join(Award, Application.award_id == Award.id)
    )

    accepted_count_distinct_by_size_query = (
        base_count_distinct_by_size_query.filter(Application.borrower_accepted_at.isnot(None)).group_by("size").all()
    )

    accepted_count_distinct_by_size = [
        StatisticData(name=row[0].strip('"') if row[0] else BorrowerSize.NOT_INFORMED, value=row[1])
        for row in accepted_count_distinct_by_size_query
    ]

    submitted_count_distinct_by_size_query = (
        base_count_distinct_by_size_query.filter(Application.borrower_submitted_at.isnot(None)).group_by("size").all()
    )

    submitted_count_distinct_by_size = [
        StatisticData(name=row[0].strip('"') if row[0] else BorrowerSize.NOT_INFORMED, value=row[1])
        for row in submitted_count_distinct_by_size_query
    ]

    approved_count_distinct_micro = (
        session.query(Borrower.id)
        .join(Application, Application.borrower_id == Borrower.id)
        .filter(Application.lender_completed_at.isnot(None))
        .filter(Borrower.size == BorrowerSize.MICRO)
        .group_by(Borrower.id)
        .count()
    )

    approved_count_distinct_micro_woman = (
        session.query(Borrower.id)
        .join(Application, Application.borrower_id == Borrower.id)
        .join(Award, Award.id == Application.award_id)
        .filter(Application.lender_completed_at.isnot(None))
        .filter(Award.source_data_contracts["g_nero_representante_legal"].astext.in_(WOMAN_VALUES))
        .filter(Borrower.size == BorrowerSize.MICRO)
        .group_by(Borrower.id)
        .count()
    )

    approved_count_distinct_by_size_query = (
        base_count_distinct_by_size_query.filter(Application.lender_completed_at.isnot(None)).group_by("size").all()
    )

    approved_count_distinct_by_size = [
        StatisticData(name=row[0].strip('"') if row[0] else BorrowerSize.NOT_INFORMED, value=row[1])
        for row in approved_count_distinct_by_size_query
    ]

    # Average credit disbursed
    total_credit_disbursed = int(
        session.query(func.sum(Application.disbursed_final_amount))
        .filter(col(Application.lender_completed_at).isnot(None))
        .scalar()
        or 0
    )

    total_credit_disbursed_micro = int(
        session.query(func.sum(Application.disbursed_final_amount))
        .join(Borrower, Borrower.id == Application.borrower_id)
        .filter(col(Application.lender_completed_at).isnot(None))
        .filter(Borrower.size == BorrowerSize.MICRO)
        .scalar()
        or 0
    )

    average_credit_disbursed_query = session.query(func.avg(Application.disbursed_final_amount)).filter(
        col(Application.lender_completed_at).isnot(None)
    )
    average_credit_disbursed = round((average_credit_disbursed_query.scalar() or 0), 2)
    average_credit_disbursed = (
        float(average_credit_disbursed) if average_credit_disbursed % 1 else int(average_credit_disbursed)
    )

    # Unique number of SMEs who accessed
    accepted_count_distinct = (
        session.query(func.count(distinct(Borrower.id)))
        .join(Application, Application.borrower_id == Borrower.id)
        .filter(col(Application.borrower_accepted_at).isnot(None))
    ).scalar() or 0

    submitted_count_distinct = (
        session.query(func.count(distinct(Borrower.id)))
        .join(Application, Application.borrower_id == Borrower.id)
        .filter(col(Application.borrower_submitted_at).isnot(None))
    ).scalar() or 0

    approved_count_distinct = (
        session.query(func.count(distinct(Borrower.id)))
        .join(Application, Application.borrower_id == Borrower.id)
        .filter(col(Application.lender_completed_at).isnot(None))
    ).scalar() or 0

    # Average applications created per day

    results_application_per_day = session.query(
        select(func.date_trunc("day", Application.created_at).label("day"), func.count().label("count_per_day"))
        .group_by(func.date_trunc("day", Application.created_at))
        .alias("daily_counts")
    ).all()

    total_count = sum(result.count_per_day for result in results_application_per_day)
    number_of_days = len(results_application_per_day)

    if number_of_days > 0:
        average_applications_per_day = round(total_count / number_of_days, 2)
        average_applications_per_day = (
            float(average_applications_per_day)
            if average_applications_per_day % 1
            else int(average_applications_per_day)
        )
    else:
        average_applications_per_day = 0

    return {
        # Mastercard reporting related statistics
        "unique_smes_contacted_by_credere": unique_smes_contacted_by_credere,
        "applications_created": total_applications,
        "accepted_count_woman": accepted_count_woman_unique,
        "approved_count": approved_count,
        "approved_count_woman": approved_count_woman,
        "total_credit_disbursed": total_credit_disbursed,
        "approved_count_distinct_micro": approved_count_distinct_micro,
        "approved_count_distinct_micro_woman": approved_count_distinct_micro_woman,
        "total_credit_disbursed_micro": total_credit_disbursed_micro,
        "accepted_count": accepted_query_count,
        "accepted_percentage": accepted_percentage,
        "sector_statistics": sectors_count,
        "rejected_reasons_count_by_reason": rejected_reasons_count_by_reason,
        "fis_chosen_by_msme": fis_chosen_by_msme,
        "accepted_count_by_gender": accepted_count_by_gender,
        "submitted_count_by_gender": submitted_count_by_gender,
        "approved_count_by_gender": approved_count_by_gender,
        "accepted_count_by_size": accepted_count_by_size,
        "submitted_count_by_size": submitted_count_by_size,
        "approved_count_by_size": approved_count_by_size,
        "accepted_count_distinct_by_gender": accepted_count_distinct_by_gender,
        "submitted_count_distinct_by_gender": submitted_count_distinct_by_gender,
        "approved_count_distinct_by_gender": approved_count_distinct_by_gender,
        "accepted_count_distinct_by_size": accepted_count_distinct_by_size,
        "submitted_count_distinct_by_size": submitted_count_distinct_by_size,
        "approved_count_distinct_by_size": approved_count_distinct_by_size,
        "average_credit_disbursed": average_credit_disbursed,
        "accepted_count_distinct": accepted_count_distinct,
        "submitted_count_distinct": submitted_count_distinct,
        "approved_count_distinct": approved_count_distinct,
        "average_applications_per_day": average_applications_per_day,
    }
