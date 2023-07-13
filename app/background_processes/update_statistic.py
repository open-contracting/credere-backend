import logging
from contextlib import contextmanager

from app.db.session import get_db

from . import statistics_utils

# any
get_statistics = statistics_utils.get_general_statistics
# OCP
get_opt_in = statistics_utils.get_msme_opt_in_stats
get_fis_choosen_by_msme = statistics_utils.get_count_of_fis_choosen_by_msme
get_proportion_of_submited_out_of_opt_in = (
    statistics_utils.get_proportion_of_submited_out_of_opt_in
)
# FI
get_msme_selecting_current_fi = (
    statistics_utils.get_proportion_of_msme_selecting_current_fi
)


def update_statistics():
    with contextmanager(get_db)() as session:
        ocp_stats = (get_statistics(session, None, None, None),)
        ocp_stats_date_test = get_statistics(session, "2022-01-01", "2022-12-31", 2)
        opt_in_stats = get_opt_in(session)
        logging.info(ocp_stats)
        logging.info(ocp_stats_date_test)
        logging.info(opt_in_stats)
        logging.info(get_msme_selecting_current_fi(session, 1))
        logging.info(get_fis_choosen_by_msme(session))
        logging.info(get_proportion_of_submited_out_of_opt_in(session))
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
