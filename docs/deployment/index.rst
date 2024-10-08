Deployment
==========

Before deploying the application, configure :doc:`../aws/index`.

After deploying the application, :ref:`cognito-admin` in Cognito.

For a list of environment variables, see :class:`~app.settings.Settings`.

Monitoring
----------

Issues and `performance <https://open-contracting-partnership.sentry.io/performance/?project=4505799907672064&statsPeriod=14d>`__ are monitored by `Sentry <https://docs.sentry.io/platforms/python/integrations/fastapi/>`__.


-  ``/applications/access-scheme`` is in *Slow HTTP Ops*, because Sentry measures the entire request, which including the background task, and not the response time.
-  Sort the *All Transactions* tab by the *Failure Rate* column, then click on a transaction and look at the *Status Breakdown* in the right sidebar, to check for potential issues to correct.

   .. note:: Infrequently accessed endpoints are likely to have a high rate, since a single error can cause a double-digit rate.

.. seealso::

   -  ``status`` `values <https://develop.sentry.dev/sdk/event-payloads/span/>`__
   -  `Performance Metrics <https://docs.sentry.io/product/performance/metrics/>`__
