:hide-toc:

Frontend integration
====================

.. note:: This page is a stub.

.. seealso:: `Credere frontend <https://github.com/open-contracting/credere-frontend>`__

Error handling
--------------

.. attention:: This behavior might be changed. :issue:`362`

An endpoint can return HTTP error status codes. The error response is JSON text with a "detail" key. The frontend uses `TanStack Query v4 <https://tanstack.com/query/v4>`__ and the ``onError`` callback of these APIs to handle these errors:

-  `useQuery <https://tanstack.com/query/v4/docs/framework/react/reference/useQuery>`__ (``onError`` is `deprecated <https://tkdodo.eu/blog/breaking-react-querys-api-on-purpose>`__)
-  `useMutation <https://tanstack.com/query/v4/docs/framework/react/reference/useMutation>`__

In some cases, this callback calls ``handleRequestError``, which looks up the ``detail`` value in ``ERRORS_MESSAGES``, and, if there's a match, it uses that message.

That is why some ``detail`` values are like ``util.ERROR_CODES.DOCUMENT_VERIFICATION_MISSING``.

Schemas and models
------------------

Credere frontend's ``/src/schemas/`` schemas should match ``app.parsers``,  ``app.serializers`` and  ``app.models`` models.

This table is contructed by running this command, and filling in information from Credere frontend's ``src/api/`` files:

.. code-block:: bash

   python -m app.commands dev routes --csv-format

.. csv-table::
   :file: _static/routes.csv
   :header-rows: 1
   :class: datatable

Enumerations
------------

Credere frontend's ``src/constants/index.ts`` constants should match ``app.models`` enumerations.

.. list-table::
   :header-rows: 1

   * - Backend
     - Frontend
   * - ApplicationStatus
     - APPLICATION_STATUS
   * - BorrowerType
     - BORROWER_TYPE
   * - CreditType
     - CREDIT_PRODUCT_TYPE
   * - BorrowerDocumentType
     - DOCUMENTS_TYPE
   * - BorrowerSize
     - MSME_TYPES
   * - StatisticCustomRange
     - STATISTICS_DATE_FILTER
   * - UserType
     - USER_TYPES