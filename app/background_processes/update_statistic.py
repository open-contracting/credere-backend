import logging
from contextlib import contextmanager

from app.db.session import get_db

from . import statistics_utils

get_statistics = statistics_utils.get_general_statistics
get_opt_in = statistics_utils.get_msme_opt_in_stats


def update_statistics():
    with contextmanager(get_db)() as session:
        ocp_stats = (get_statistics(session, None, None, None),)
        ocp_stats_date_test = get_statistics(session, "2022-01-01", "2022-12-31", 2)
        opt_in_stats = get_opt_in(session)
        logging.info(ocp_stats)
        logging.info(ocp_stats_date_test)
        logging.info(opt_in_stats)
        # logging.info(fi_stats)
        # try:
        #     # save to statistics DB

        # except Exception as e:
        #     logging.error(f"there was an error setting to lapsed: {e}")
        #     session.rollback()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Output logs to the console
    )
    update_statistics()
