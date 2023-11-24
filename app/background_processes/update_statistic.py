import logging
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import Date, cast
from sqlalchemy.orm import Session

from app.db.session import get_db, transaction_session_logger
from app.schema import core
from app.schema.statistic import Statistic, StatisticType

from . import statistics_utils

logger = logging.getLogger(__name__)

# any
get_statistics_kpis = statistics_utils.get_general_statistics
# OCP
get_msme_opt_in = statistics_utils.get_msme_opt_in_stats


def update_statistics(db_provider: Session = get_db):
    """
    Update and store various statistics related to applications and lenders in the database.

    This function retrieves and logs different types of statistics related to applications
    and lenders. It uses the `get_general_statistics`, `get_msme_opt_in_stats`,
    and `get_count_of_fis_choosen_by_msme` functions from the `statistics_utils` module
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
            statistic_kpis = get_statistics_kpis(session, None, None, None)
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
            statistics_msme_opt_in = get_msme_opt_in(session)
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
            lender_ids = [id[0] for id in session.query(core.Lender.id).all()]
            for lender_id in lender_ids:
                # Get statistics for each lender
                statistic_kpis = get_statistics_kpis(session, None, None, lender_id)

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
