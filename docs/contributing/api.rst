API design
==========

.. seealso:: `Library and Web API <https://ocp-software-handbook.readthedocs.io/en/latest/general/api.html#web-api>`__

-  Use the parameter ``id`` only for application IDs, to avoid accidental errors.
-  Don't use ``status.HTTP_400_BAD_REQUEST``. FastAPI uses it for `request validation errors <https://fastapi.tiangolo.com/tutorial/handling-errors/?h=#override-request-validation-exceptions>`__, which are reported to Sentry. Instead, use:

   -  ``status.HTTP_403_FORBIDDEN``, if not authenticated or authorized

      .. note:: 401 is only relevant to `HTTP authentication <https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication>`__. `RFC 7325 <https://www.rfc-editor.org/rfc/rfc7235#section-3.1>`__ states: "The server generating a 401 response MUST send a WWW-Authenticate header field"

   -  ``status.HTTP_404_NOT_FOUND``, if the resource is not found
   -  ``status.HTTP_409_CONFLICT``, if the resource already exists
   -  ``status.HTTP_501_NOT_IMPLEMENTED``, if the code path is not implemented
   -  ``status.HTTP_422_UNPROCESSABLE_ENTITY`` for problems with the request, otherwise

   .. seealso::

      -  `422 Unprocessable Content <https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/422>`__ (MDN)
      -  `Choosing an HTTP Status Code <https://www.codetinkerer.com/2015/12/04/choosing-an-http-status-code.html>`__
