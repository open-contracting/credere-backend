Frontend integration
====================

.. note:: This page is a stub.

.. seealso:: `Credere frontend <https://github.com/open-contracting/credere-frontend>`__

Schemas
-------

The schemas under Credere frontend's ``/src/schemas/`` directory should match the models in the ``app/parsers.py`` file.

Error handling
--------------

.. attention:: This behavior might be changed. :issue:`362`

An endpoint can return HTTP error status codes. The error response is JSON text with a "detail" key. The frontend uses `TanStack Query v4 <https://tanstack.com/query/v4>`__ and the ``onError`` callback of these APIs to handle these errors:

-  `useQuery <https://tanstack.com/query/v4/docs/framework/react/reference/useQuery>`__ (``onError`` is `deprecated <https://tkdodo.eu/blog/breaking-react-querys-api-on-purpose>`__)
-  `useMutation <https://tanstack.com/query/v4/docs/framework/react/reference/useMutation>`__

In some cases, this callback calls ``handleRequestError``, which looks up the ``detail`` value in ``ERRORS_MESSAGES``, and, if there's a match, it uses that message.

That is why some ``detail`` values are like ``util.ERROR_CODES.DOCUMENT_VERIFICATION_MISSING``.
