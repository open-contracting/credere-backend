import logging
from contextlib import contextmanager
from datetime import datetime

from app.db.session import get_db
from app.schema.statistic import Statistic, StatisticType

from . import statistics_utils

# any
get_statistics_kpis = statistics_utils.get_general_statistics
# OCP
get_msme_opt_in = statistics_utils.get_msme_opt_in_stats


def update_statistics():
    with contextmanager(get_db)() as session:
        logging.info(get_statistics_kpis(session, None, None, 2))
        logging.info(get_statistics_kpis(session, "2022-01-01", "2022-12-31", 2))

        # logging.info(get_msme_opt_in(session))

        # se van almacernar en la DB los datos por lender
        # lo de FI no voy a almacenar porque es especifico del lender
        try:
            # Get general statistics
            statistic_kpis = get_statistics_kpis(session, None, None, None)
            statistics_msme_opt_in = get_msme_opt_in(session)
            statistics_msme_opt_in["sector_statistics"] = [
                data.dict() for data in statistics_msme_opt_in["sector_statistics"]
            ]
            statistics_msme_opt_in["rejected_reasons_count_by_reason"] = [
                data.dict()
                for data in statistics_msme_opt_in["rejected_reasons_count_by_reason"]
            ]
            statistics_msme_opt_in["fis_choosen_by_msme"] = [
                data.dict() for data in statistics_msme_opt_in["fis_choosen_by_msme"]
            ]

            insert_kpis = Statistic(
                type=StatisticType.APPLICATION_KPIS,
                data=statistic_kpis,
                created_at=datetime.now(),
            )
            session.add(insert_kpis)

            insert_statistics_msme_opt_in = Statistic(
                type=StatisticType.MSME_OPT_IN_STATISTICS,
                data=statistics_msme_opt_in,
                created_at=datetime.now(),
            )
            session.add(insert_statistics_msme_opt_in)

            session.commit()

        except Exception as e:
            logging.error(f"there was an error saving statistics: {e}")
            session.rollback()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Output logs to the console
    )
    update_statistics()
