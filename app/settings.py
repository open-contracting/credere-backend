# https://fastapi.tiangolo.com/advanced/settings/#pydantic-settings

import logging.config
import re
from typing import Any

import sentry_sdk
from pydantic_settings import BaseSettings, SettingsConfigDict


def sentry_filter_transactions(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """
    Filter transactions to be sent to Sentry.
    This function prevents transactions that interact with Cognito from being sent to Sentry.

    :param event: The event data.
    :param hint: A dictionary of extra data passed to the function.
    :return: The event data if it should be sent to Sentry, otherwise None.
    """
    data_url = event["breadcrumbs"]["values"][0]["data"]["url"] or None
    if data_url and re.search(r"https://cognito-idp.*\.amazonaws\.com", data_url):
        return None
    return event


class Settings(BaseSettings):
    """
    Each setting has a corresponding uppercase environment variable.

    .. seealso:: `Settings Management <https://docs.pydantic.dev/latest/concepts/pydantic_settings/#usage>`__
    """

    #: If "production", emails all recipients. Otherwise, emails lenders and
    #: :attr:`~app.settings.Settings.ocp_email_group` only, replacing borrower email addresses with
    #: :attr:`~app.settings.Settings.test_mail_receiver`.
    environment: str = "development"
    #: The `logging level <https://docs.python.org/3/library/logging.html#levels>`__ of the root logger.
    log_level: int | str = logging.INFO
    #: PostgreSQL connection string.
    database_url: str = "postgresql:///credere_backend?application_name=credere_backend"
    #: PostgreSQL connection string that overrides ``DATABASE_URL`` (:ref:`tests<dev-tests>` drops the database).
    test_database_url: str = ""

    # Security

    #: The secret key with which to hash borrower identifiers (to allow for deduplication even after the borrower's
    #: information has been removed).
    #:
    #: .. seealso:: :func:`app.util.get_secret_hash`
    hash_key: str = ""
    #: The maximum file size of uploaded documents or uploaded contracts (sync with ``VITE_MAX_FILE_SIZE_MB`` in
    #: Credere frontend).
    #:
    #: .. seealso:: :func:`app.util.validate_file`
    max_file_size_mb: int = 5

    # Timeline

    #: The number of days after the application is created, after which a PENDING or DECLINED application becomes
    #: inaccessible to the borrower.
    #:
    #: .. seealso::
    #:
    #:    -  :attr:`~app.settings.Settings.reminder_days_before_expiration`
    #:    -   :typer:`python-m-app-fetch-awards`
    application_expiration_days: int = 7
    #: The number of days before a PENDING application's expiration date, past which the borrower is sent a reminder.
    #:
    #: .. seealso::
    #:
    #:    -  :attr:`~app.settings.Settings.application_expiration_days`
    #:    -  :attr:`app.models.Application.pending_introduction_reminder`
    reminder_days_before_expiration: int = 3
    #: The number of days before an ACCEPTED application's lapsed date, past which the borrower is sent a reminder.
    #:
    #: .. seealso::
    #:
    #:    -  :attr:`~app.settings.Settings.days_to_change_to_lapsed`
    #:    -  :attr:`app.models.Application.pending_submission_reminder`
    reminder_days_before_lapsed: int = 3
    #: Lenders agree to respond to application changes (STARTED, CONTRACT_UPLOADED) within a number of days, known as
    #: Service Level Agreement (SLA) days (:attr:`app.models.Lender.sla_days`).
    #:
    #: This is the ratio of SLA days for which to wait for the lender to respond, after which an application is
    #: overdue, and the lender is sent a reminder.
    #:
    #: For example, if set to 0.7, a lender with 10 SLA days receives the first reminder after an application has been
    #: waiting for the lender to respond for 7 days.
    #:
    #: .. seealso::
    #:
    #:    -  :typer:`python-m-app-sla-overdue-applications`
    #:    -  :meth:`app.models.Application.days_waiting_for_lender`
    progress_to_remind_started_applications: float = 0.7
    #: The number of days for which to wait for the borrower to respond, after which an application becomes LAPSED.
    #:
    #: .. seealso:: :meth:`app.models.Application.lapseable`
    days_to_change_to_lapsed: int = 14
    #: The number of days after the application reaches a final state, after which the application is archived.
    #:
    #: .. seealso:: :meth:`app.models.Application.archivable`
    days_to_erase_borrowers_data: int = 7

    # Data sources

    #: The application token to the `SECOP API <https://datos.gov.co/profile/edit/developer_settings>`__.
    colombia_secop_app_token: str = ""
    #: The number of items to retrieve at once in :typer:`python-m-app-fetch-awards`.
    secop_pagination_limit: int = 5
    #: The number of days of past items to retrieve the first time :typer:`python-m-app-fetch-awards` runs.
    secop_default_days_from_ultima_actualizacion: int = 365

    # Email addresses

    #: The verified email address in :doc:`Amazon SES</aws/ses>` to use as the FROM email address.
    email_sender_address: str = "credere@noreply.open-contracting.org"
    #: The email address of Credere administrators, to notify about new and overdue applications.
    #:
    #: .. seealso:: :attr:`~app.settings.Settings.progress_to_remind_started_applications`
    ocp_email_group: str = "credere@noreply.open-contracting.org"  # should not be a noreply in production
    #: The email address with which to replace borrower email addresses in a non-production
    #: :attr:`~app.settings.Settings.environment` (for example, your own email address).
    test_mail_receiver: str = "credere@noreply.open-contracting.org"

    # Email templates

    #: The base URL of Credere.
    frontend_url: str = "http://localhost:3000"  # also for CORS
    #: The language of the email templates to use.
    email_template_lang: str = "es"
    #: The URL of OCP's Facebook profile.
    facebook_link: str = "https://www.facebook.com/OpenContracting/"
    #: The URL of OCP's Twitter profile.
    twitter_link: str = "https://twitter.com/opencontracting"
    #: The base URL of Credere.
    link_link: str = "http://localhost:3000"
    #: The base URL of Credere's images directory (can be a CDN URL).
    images_base_url: str = "https://credere.open-contracting.org/images"

    # Third-party services

    #: Amazon Web Services region.
    aws_region: str = "us-west-2"
    #: :doc:`Operational user</aws/iam>` access key.
    aws_access_key: str = ""
    #: :doc:`Operational user</aws/iam>` client secret.
    aws_client_secret: str = ""
    #: :doc:`Cognito</aws/cognito>` user pool ID.
    cognito_pool_id: str = ""
    #: :doc:`Cognito</aws/cognito>` app client ID.
    cognito_client_id: str = ""
    #: :doc:`Cognito</aws/cognito>` app client secret.
    cognito_client_secret: str = ""
    #: Sentry DSN.
    sentry_dsn: str = ""

    model_config = SettingsConfigDict(env_file=".env")


app_settings = Settings()

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "console": {
                "format": "%(asctime)s %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
            },
        },
        "loggers": {
            "": {
                "handlers": ["console"],
                "level": app_settings.log_level,
            },
        },
    }
)

if app_settings.sentry_dsn:
    sentry_sdk.init(
        dsn=app_settings.sentry_dsn,
        before_send=sentry_filter_transactions,
        # Set traces_sample_rate to 1.0 to capture 100% of transactions for performance monitoring.
        traces_sample_rate=1.0,
    )
