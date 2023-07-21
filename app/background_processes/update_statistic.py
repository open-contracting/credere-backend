import logging
from contextlib import contextmanager

from app.db.session import get_db
from app.schema.statistic import Statistic, StatisticType

from . import statistics_utils

# any
get_statistics_kpis = statistics_utils.get_general_statistics
# OCP
get_msme_opt_in = statistics_utils.get_msme_opt_in_stats
get_fis_choosen_by_msme = statistics_utils.get_count_of_fis_choosen_by_msme


def update_statistics():
    """
    Update and store various statistics related to applications and lenders in the database.

    This function retrieves and logs different types of statistics related to applications
    and lenders. It uses the `get_general_statistics`, `get_msme_opt_in_stats`,
    and `get_count_of_fis_choosen_by_msme` functions from the `statistics_utils` module
    to fetch the respective statistics. The retrieved statistics are then logged using
    the `logging.info()` function.

    After fetching the general statistics, this function attempts to store them in the database
    as an instance of the `Statistic` model. The statistics are stored with the type set to
    `StatisticType.APPLICATION_KPIS`. The `Statistic` model contains a JSON field to store
    the actual statistical data.

    If an error occurs during the process, it is caught and logged using `logging.error()`.
    The database session is rolled back in case of an exception to prevent any changes from
    being committed to the database.

    Note:
    - The function utilizes the `get_db()` context manager to open a database session.
    - The logging level and format are configured using `logging.basicConfig()`.

    Example usage:
    >>> update_statistics()
    """
    with contextmanager(get_db)() as session:
        logging.info(get_statistics_kpis(session, None, None, 2))
        logging.info(get_statistics_kpis(session, "2022-01-01", "2022-12-31", 2))

        logging.info(get_msme_opt_in(session))

        logging.info(get_fis_choosen_by_msme(session))

        # se van almacernar en la DB los datos por lender
        # lo de FI no voy a almacenar porque es especifico del lender
        try:
            statistic_kpis = get_statistics_kpis(
                session, None, None, None
            )  # Get general statistics
            statistics = Statistic(
                type=StatisticType.APPLICATION_KPIS,
                data=statistic_kpis,
            )
            session.add(statistics)
            session.commit()
        except Exception as e:
            logging.error(f"there was an error setting to lapsed: {e}")
            session.rollback()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Output logs to the console
    )
    update_statistics()
