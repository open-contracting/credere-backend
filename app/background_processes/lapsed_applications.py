import logging
from contextlib import contextmanager
from datetime import datetime

from app.db.session import get_db
from app.schema.core import ApplicationStatus

from . import application_utils

get_lapses_applications = application_utils.get_lapsed_applications


def set_lapsed_applications():
    with contextmanager(get_db)() as session:
        lapsed_applications = get_lapses_applications(session)
        logging.info("Quantity of lapsed application " + str(len(lapsed_applications)))
        if len(lapsed_applications) == 0:
            logging.info("No application to remove data")
        else:
            for application in lapsed_applications:
                try:
                    # save to DB
                    application.status = ApplicationStatus.LAPSED
                    application.application_lapsed_at = datetime.utcnow()
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
    set_lapsed_applications()
