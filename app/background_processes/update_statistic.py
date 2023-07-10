import logging
from contextlib import contextmanager

from app.db.session import get_db

from . import statistics_utils

get_ocp_statistics = statistics_utils.get_ocp_statistics
get_fi_statistics = statistics_utils.get_fi_statistics


def update_statistics():
    with contextmanager(get_db)() as session:
        ocp_stats = get_ocp_statistics(session)
        fi_stats = get_fi_statistics(session)
        logging.info(ocp_stats)
        logging.info(fi_stats)
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
