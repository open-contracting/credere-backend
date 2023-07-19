from app.background_processes.update_statistic import update_statistics
from tests.common import common_test_client

from tests.common.common_test_client import start_background_db  # isort:skip # noqa
from tests.common.common_test_client import mock_ses_client  # isort:skip # noqa
from tests.common.common_test_client import mock_cognito_client  # isort:skip # noqa
from tests.common.common_test_client import app, client  # isort:skip # noqa


def test_update_statistic(start_background_db):  # noqa
    update_statistics(common_test_client.get_test_db)
