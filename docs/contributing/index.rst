Contributing
============

.. toctree::
   :caption: contents

   sqlalchemy

.. seealso::

   `ADRs for models.py and sources/colombia.py <https://drive.google.com/drive/folders/1WtrwJH3kSQNxt9K-sa1s4O8HbwkLzcEA>`__

Setup
-----

Install requirements:

.. code-block:: bash

   pip install -r requirements_dev.txt -r docs/requirements.txt

If requirements are updated, re-run this command.

Install the git pre-commit hooks:

.. code-block:: bash

   pre-commit install

Create a ``.env`` file, using ``.envtest`` as an example.

Create development and test databases in PostgreSQL, and set the :attr:`DATABASE_URL<app.settings.Settings.database_url>` and :attr:`TEST_DATABASE_URL<app.settings.TEST_DATABASE_URL>` environment variables one at a time, for example:

.. code-block:: bash

   DATABASE_URL=postgresql://{username}:{password}@{host:port}/{db_name}

Run database migrations:

.. code-block:: bash

   alembic upgrade head

Repository structure
--------------------

.. tree app/ -I '__pycache__'

.. code-block:: none

   app/
   ├── __init__.py
   ├── auth.py              # Permissions and JWT token verification
   ├── aws.py               # Amazon Web Services API clients
   ├── commands.py          # Typer commands
   ├── db.py                # SQLAlchemy database operations and session management
   ├── dependencies.py      # FastAPI dependencies
   ├── exceptions.py        # Definitions of exceptions raised by this application
   ├── i18n.py              # Internationalization support
   ├── mail.py              # Email sending
   ├── main.py              # FastAPI application entry point
   ├── models.py            # SQLAlchemy models
   ├── parsers.py           # Pydantic models to parse query string arguments
   ├── routers              # FastAPI routers
   │   ├── __init__.py
   │   ├── guest            # FastAPI routers for passwordless URLs
   │   │   └── {...}.py
   │   └── {...}.py
   ├── serializers.py       # Pydantic models to serialize API responses
   ├── settings.py          # Environment settings and Sentry configuration
   ├── sources              # Data sources for contracts, awards, and borrowers
   │   ├── __init__.py
   │   ├── util.py
   │   └── colombia.py
   ├── util.py              # Utilities used by routers, background tasks and commands
   └── utils
       ├── __init__.py
       ├── statistics.py    # Statistics functions used by statistics routers, background tasks and commands
       └── tables.py        # Functions for generating tables in downloadable documents

Tasks
-----

Update requirements
~~~~~~~~~~~~~~~~~~~

See `Requirements <https://ocp-software-handbook.readthedocs.io/en/latest/python/requirements.html>`__ in the OCP Software Development Handbook.

Run server
~~~~~~~~~~

.. code-block:: bash

   uvicorn app.main:app --reload

.. _dev-tests:

Run tests
~~~~~~~~~

The :attr:`DATABASE_URL<app.settings.Settings.database_url>` and :attr:`TEST_DATABASE_URL<app.settings.TEST_DATABASE_URL>` environment variables must be set to the test database.

.. code-block:: bash

   pytest -W error

Check coverage:

.. code-block:: bash

   pytest --cov

Generate coverage HTML report:

.. code-block:: bash

   coverage html

You can the open ``htmlcov/index.html`` in a browser.

Run shell
~~~~~~~~~

For example:

.. code-block:: python

   from sqlalchemy import create_engine
   from sqlalchemy.orm import Session
   from sqlmodel import col
   from app import models
   engine = create_engine("postgresql:///credere", echo=True)
   session = Session(engine)

And then run queries with ``session``.

Create database migration
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   alembic revision -m "migration name"

This generates a file like ``2ca870aa737d_migration_name.py``.

Then, edit both functions, ``upgrade`` and ``downgrade``.

Alternatively, run:

.. code-block:: bash

   alembic revision --autogenerate -m "migration name"

This attempts to auto-detect the changes made to ``models.py``, subject to `limitations <https://alembic.sqlalchemy.org/en/latest/autogenerate.html#what-does-autogenerate-detect-and-what-does-it-not-detect>`__.

Build documentation
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   sphinx-autobuild -q docs docs/_build/html --watch .

Run application as Docker
~~~~~~~~~~~~~~~~~~~~~~~~~

Create an image:

.. code-block:: bash

   docker build -t {image_name} .

Create and run a container:

.. code-block:: bash

   docker run -d --name {container_name} -p 8000:8000 {image_name}

To delete the image (e.g. when recreating it), run:

.. code-block:: bash

   docker rmi <your-image-id>

Development
-----------

Read this section and the :doc:`../api/index` to learn about helper methods and application logic.

API endpoints naming conventions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use lowercase letters and separate words with hyphens or underscores.

   Example: GET /users or GET /users/all

If the endpoint retrieves a specific resource, use the resource name in its singular form.

   Example: GET /user/{id} or PUT /user/{id}

For endpoints that return collections of resources, use plural nouns.

   Example: GET /users or POST /users

Use sub-resources to represent relationships between resources.

   Example: GET /users/{id}/orders or GET /users/{id}/invoices

For actions or operations that do not fit into the RESTful resource model, consider using verbs or descriptive phrases.

   Example: POST /users/{id}/reset-password or PUT /users/{id}/activate

Avoid using abbreviations or acronyms unless they are widely understood and agreed upon within your development team or industry.

Ensure that the endpoint names are self-explanatory and reflect the purpose of the API operation.
