import logging
from contextlib import contextmanager

from app.db.session import get_db

from . import statistics_utils

get_statistics = statistics_utils.get_statistics


def update_statistics():
    with contextmanager(get_db)() as session:
        total_applications_received = get_statistics(session)
        logging.info("full dictionary" + str(total_applications_received))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Output logs to the console
    )
    update_statistics()
