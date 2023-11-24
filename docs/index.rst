Credere backend
===============

Repository structure
--------------------

.. tree app/ -I '__pycache__'

.. code-block:: none

   app/
   ├── __init__.py
   ├── auth.py              # Permissions and JWT token verification
   ├── aws.py               # Amazon Web Services API clients
   ├── commands.py          # Typer commands to run background processes
   ├── db.py                # SQLAlchemy database operations and session management
   ├── exceptions.py        # Definitions of exceptions raised by this application
   ├── i18n.py              # Internationalization support
   ├── mail.py              # Email sending
   ├── main.py              # FastAPI application entry point
   ├── models.py            # SQLAlchemy models
   ├── parsers.py           # Pydantic models to parse query string arguments
   ├── routers              # FastAPI routers
   │   ├── __init__.py
   │   ├── applications.py
   │   ├── awards.py
   │   ├── borrowers.py
   │   ├── lenders.py
   │   ├── security.py
   │   ├── statistics.py
   │   └── users.py
   ├── serializers.py       # Pydantic models to serialize API responses
   ├── settings.py          # Environment settings and Sentry configuration
   ├── sources              # Data sources for contracts, awards, and borrowers
   │   ├── __init__.py
   │   ├── util.py
   │   └── colombia.py
   ├── util.py              # Utilities used by both routers and background tasks
   └── utils
       ├── __init__.py
       ├── applications.py  # Functions used by the application router only
       ├── background.py    # Functions used by background tasks only
       └── statistics.py    # Statistics functions used by statistics routers and background tasks
