import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Callable, Generator

from sqlalchemy import Date, Integer, cast, distinct, func, text
from sqlalchemy.orm import Query, Session
from sqlmodel import col

from app.db import get_db, transaction_session_logger
from app.models import (
    Application,
    ApplicationStatus,
    Borrower,
    CreditProduct,
    CreditType,
    Lender,
    Statistic,
    StatisticData,
    StatisticType,
)

logger = logging.getLogger(__name__)


def update_statistics(db_provider: Callable[[], Generator[Session, None, None]] = get_db) -> None:
    """
    Update and store various statistics related to applications and lenders in the database.

    This function retrieves and logs different types of statistics related to applications
    and lenders. It uses the `get_general_statistics`, `get_msme_opt_in_stats`,
    and `get_count_of_fis_choosen_by_msme` functions
    to fetch the respective statistics. The retrieved statistics are then logged using
    the `logger.info()` function.

    After fetching the general statistics, this function attempts to store them in the database
    as an instance of the `Statistic` model. The statistics are stored with the type set to
    `StatisticType.APPLICATION_KPIS`. The `Statistic` model contains a JSON field to store
    the actual statistical data.

    If an error occurs during the process, it is caught and logged using `logger.exception()`.
    The database session is rolled back in case of an exception to prevent any changes from
    being committed to the database.

    Note:
    - The function utilizes the `get_db()` context manager to open a database session.

    Example usage:
    >>> update_statistics()
    """

    with contextmanager(db_provider)() as session:
        with transaction_session_logger(session, "Error saving statistics"):
            # Get general Kpis
            statistic_kpis = get_general_statistics(session, None, None, None)
            # Try to get the existing row
            statistic_kpi_data = (
                session.query(Statistic)
                .filter(
                    cast(Statistic.created_at, Date) == datetime.today().date(),
                    Statistic.type == StatisticType.APPLICATION_KPIS,
                )
                .first()
            )

            # If it exists, update it
            if statistic_kpi_data:
                statistic_kpi_data.data = statistic_kpis
            # If it doesn't exist, create a new one
            else:
                statistic_kpi_data = Statistic(
                    type=StatisticType.APPLICATION_KPIS,
                    data=statistic_kpis,
                    created_at=datetime.now(),
                )
                session.add(statistic_kpi_data)

            # Get Opt in statistics
            statistics_msme_opt_in = get_msme_opt_in_stats(session)
            statistics_msme_opt_in["sector_statistics"] = [
                data.dict() for data in statistics_msme_opt_in["sector_statistics"]
            ]
            statistics_msme_opt_in["rejected_reasons_count_by_reason"] = [
                data.dict() for data in statistics_msme_opt_in["rejected_reasons_count_by_reason"]
            ]
            statistics_msme_opt_in["fis_choosen_by_msme"] = [
                data.dict() for data in statistics_msme_opt_in["fis_choosen_by_msme"]
            ]
            # Try to get the existing row
            statistic_opt_data = (
                session.query(Statistic)
                .filter(
                    cast(Statistic.created_at, Date) == datetime.today().date(),
                    Statistic.type == StatisticType.MSME_OPT_IN_STATISTICS,
                )
                .first()
            )

            # If it exists, update it
            if statistic_opt_data:
                statistic_opt_data.data = statistics_msme_opt_in
            # If it doesn't exist, create a new one
            else:
                statistic_opt_data = Statistic(
                    type=StatisticType.MSME_OPT_IN_STATISTICS,
                    data=statistics_msme_opt_in,
                    created_at=datetime.now(),
                )
                session.add(statistic_opt_data)

            # Get general Kpis for every lender
            lender_ids = [id[0] for id in session.query(Lender.id).all()]
            for lender_id in lender_ids:
                # Get statistics for each lender
                statistic_kpis = get_general_statistics(session, None, None, lender_id)

                # Try to get the existing row
                statistic_kpi_data = (
                    session.query(Statistic)
                    .filter(
                        cast(Statistic.created_at, Date) == datetime.today().date(),
                        Statistic.type == StatisticType.APPLICATION_KPIS,
                        Statistic.lender_id == lender_id,
                    )
                    .first()
                )

                # If it exists, update it
                if statistic_kpi_data:
                    statistic_kpi_data.data = statistic_kpis
                # If it doesn't exist, create a new one
                else:
                    statistic_kpi_data = Statistic(
                        type=StatisticType.APPLICATION_KPIS,
                        data=statistic_kpis,
                        lender_id=lender_id,
                        created_at=datetime.now(),
                    )

                session.add(statistic_kpi_data)


def _get_base_query(
    sessionBase: "Query[Application]",
    start_date: datetime | str | None,
    end_date: datetime | str | None,
    lender_id: int | None,
) -> "Query[Application]":
    """
    Create the base query for filtering applications based on the provided start_date, end_date, and lender_id.

    This function creates the base query for filtering applications from the database. The filtering is based on
    the provided start_date, end_date, and lender_id (if available).

    :param sessionBase: The base query representing the Application model.
    :param start_date: The start date for filtering applications. (default: None)
    :param end_date: The end date for filtering applications. (default: None)
    :param lender_id: The ID of the lender for filtering applications. (default: None)
    :return: The base query for filtering applications.
    """

    base_query = None
    if start_date is not None and end_date is not None:
        base_query = sessionBase.filter(
            col(Application.created_at) >= start_date,
            col(Application.created_at) <= end_date,
        )
    elif start_date is not None:
        base_query = sessionBase.filter(col(Application.created_at) >= start_date)
    elif end_date is not None:
        base_query = sessionBase.filter(col(Application.created_at) <= end_date)
    else:
        base_query = sessionBase

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


# Group of Stat only for OCP USER (msme opt in stats)
def get_msme_opt_in_stats(session: Session) -> dict[str, Any]:
    """
    Get statistics specific to MSME opt-in applications.

    This function retrieves statistics specific to MSME opt-in applications. The statistics include the count of
    applications opted-in, the percentage of applications opted-in, statistics related to different sectors, and
    counts of declined reasons.

    :return: A dictionary containing the statistics specific to MSME opt-in applications.
    """

    logger.info("calculating msme opt in stas for lender ")

    # opt in--------
    opt_in_query = session.query(Application).filter(col(Application.borrower_accepted_at).isnot(None))
    opt_in_query_count = opt_in_query.count()

    # opt in %--------
    total_applications = session.query(Application).count()
    if total_applications != 0:
        opt_in_percentage = (
            session.query(Application).filter(col(Application.borrower_accepted_at).isnot(None)).count()
            / total_applications
        ) * 100
        opt_in_percentage = round(opt_in_percentage, 2)
    else:
        opt_in_percentage = 0

    # opt proportion by sector %--------
    # Calculate total submitted application count
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
    fis_choosen_by_msme_query = (
        session.query(Lender.name, func.count(Application.id))
        .join(Lender, Application.lender_id == Lender.id)
        .filter(col(Application.borrower_submitted_at).isnot(None))
        .group_by(Lender.name)
        .all()
    )
    fis_choosen_by_msme = [StatisticData(name=row[0], value=row[1]) for row in fis_choosen_by_msme_query]

    opt_in_statistics = {
        "opt_in_query_count": opt_in_query_count,
        "opt_in_percentage": opt_in_percentage,
        "sector_statistics": sectors_count,
        "rejected_reasons_count_by_reason": rejected_reasons_count_by_reason,
        "fis_choosen_by_msme": fis_choosen_by_msme,
    }

    return opt_in_statistics


# Stat only for OCP USER Bars graph
def get_count_of_fis_choosen_by_msme(session: Session) -> list[StatisticData]:
    """
    Get the count of Financial Institutions (FIs) chosen by MSMEs.

    This function retrieves the count of Financial Institutions (FIs) chosen by MSMEs for their applications.

    :return: A list of StatisticData objects containing the count of FIs chosen by MSMEs.
    """

    fis_choosen_by_msme_query = (
        session.query(Lender.name, func.count(Application.id))
        .join(Lender, Application.lender_id == Lender.id)
        .filter(col(Application.borrower_submitted_at).isnot(None))
        .group_by(Lender.name)
        .all()
    )

    return [StatisticData(name=row[0], value=row[1]) for row in fis_choosen_by_msme_query]
