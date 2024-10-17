:hide-toc:

Frontend integration
====================

.. seealso:: `Credere frontend <https://github.com/open-contracting/credere-frontend>`__

Enumerations
------------

Credere frontend's ``src/constants/index.ts`` constants should match ``app.models`` enumerations.

.. list-table::
   :header-rows: 1

   * - Backend
     - Frontend
   * - ApplicationStatus
     - APPLICATION_STATUS
   * - BorrowerSize.NOT_INFORMED
     - DEFAULT_BORROWER_SIZE
   * - CreditType
     - CREDIT_PRODUCT_TYPE
   * - UserType
     - USER_TYPES

… and also ``app.util`` enumerations.

.. list-table::
   :header-rows: 1

   * - Backend
     - Frontend
   * - StatisticCustomRange
     - STATISTICS_DATE_FILTER

Schemas and models
------------------

Credere frontend's ``src/schemas/`` schemas should match ``app.parsers``,  ``app.serializers`` and  ``app.models`` models.

This table is contructed by running this command, and filling in information from Credere frontend's ``src/api/`` files:

.. code-block:: bash

   uv run python -m app dev routes --csv-format --file docs/_static/routes.csv

.. csv-table::
   :file: _static/routes.csv
   :header-rows: 1
   :class: datatable
