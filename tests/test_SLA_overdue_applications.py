import logging

from app.background_processes import SLA_overdue_applications
from tests.common import common_test_client

from tests.common.common_test_client import start_background_db  # isort:skip # noqa
from tests.common.common_test_client import mock_ses_client  # isort:skip # noqa
from tests.common.common_test_client import mock_cognito_client  # isort:skip # noqa
from tests.common.common_test_client import app, client  # isort:skip # noqa


def test_send_overdue_reminders(start_background_db):  # noqa
    logging.info("Sending SLA overdue reminder notifications")
    SLA_overdue_applications.SLA_overdue_applications(common_test_client.get_test_db)
