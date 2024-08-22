Contributing
============

.. toctree::
   :caption: contents

   sqlalchemy

.. seealso::

   `ADRs for models.py and sources/colombia.py <https://drive.google.com/drive/folders/1WtrwJH3kSQNxt9K-sa1s4O8HbwkLzcEA>`__

Setup
-----

#. Install the requirements:

   .. code-block:: bash

      pip install -r requirements_dev.txt -r docs/requirements.txt

   .. note::

      If requirements are updated in git, re-run this command.

#. Set up the git pre-commit hook:

   .. code-block:: bash

      pre-commit install

#. Create development and test databases. To use the default ``DATABASE_URL``, create a database named ``credere_backend`` to which your shell user has access.

   To customize settings (for example, to use a different ``DATABASE_URL``), create a ``.env`` file based on the ``.env.example`` file.

#. Run database migrations:

   .. code-block:: bash

      alembic upgrade head

#. Install the entry point for Babel:

   .. code-block:: bash

      pip install -e .

#. Compile message catalogs:

   .. code-block:: bash

      pybabel compile -f -d locale

Repository structure
--------------------

.. tree app/ -I '__pycache__'

.. code-block:: none

   email_templates/         # HTML fragments
   app/
   ├── __init__.py
   ├── __main__.py          # Typer commands
   ├── auth.py              # Permissions and JWT token verification
   ├── aws.py               # Amazon Web Services API clients
   ├── babel.py             # Babel extractors
   ├── db.py                # SQLAlchemy database operations and session management
   ├── dependencies.py      # FastAPI dependencies
   ├── exceptions.py        # Definitions of exceptions raised by this application
   ├── i18n.py              # Internationalization support
   ├── mail.py              # Email sending
   ├── main.py              # FastAPI application entry point
   ├── models.py            # SQLAlchemy models
   ├── parsers.py           # Pydantic models to parse query strings and request bodies
   ├── routers              # FastAPI routers
   │   ├── __init__.py
   │   ├── guest            # FastAPI routers for passwordless URLs
   │   │   └── {...}.py
   │   └── {...}.py
   ├── serializers.py       # Pydantic models to serialize API responses
   ├── settings.py          # Environment settings and Sentry configuration
   ├── sources              # Data sources for contracts, awards, and borrowers
   │   ├── __init__.py
   │   └── colombia.py
   ├── util.py              # Utilities used by routers, background tasks and commands
   └── utils
       ├── __init__.py
       ├── statistics.py    # Statistics functions used by statistics routers, background tasks and commands
       └── tables.py        # Functions for generating tables in downloadable documents

Run commands
------------

.. _dev-server:

Run server
~~~~~~~~~~

.. code-block:: bash

   uvicorn app.main:app --reload

.. _dev-tests:

Run tests
~~~~~~~~~

The :attr:`DATABASE_URL<app.settings.Settings.database_url>` and :attr:`TEST_DATABASE_URL<app.settings.Settings.test_database_url>` environment variables must be set to the test database.

.. code-block:: bash

   pytest -W error --cov app

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

   docker rmi {image_id}

Make changes
------------

Read the next pages in this section to learn about style guides, and the :doc:`../api/index` about helper methods and application logic. See also the `OCP Software Development Handbook <https://ocp-software-handbook.readthedocs.io/en/latest/>`__, in particular:

-  `Library and Web API <https://ocp-software-handbook.readthedocs.io/en/latest/general/api.html#web-api>`__
-  `Python <https://ocp-software-handbook.readthedocs.io/en/latest/python/>`__

Style guide
~~~~~~~~~~~

-  Use lowercase filenames, including ``email_templates/`` files.

In Python code and documentation:

-  Use "lender", not "FI" or "financial institution".
-  Use "borrower", not "MSME", "SME" or "small and medium-sized enterprises".

.. note::

   Some endpoints and enums cannot be made to conform to this style guide, without migrating the database or updating the frontend.

Update requirements
~~~~~~~~~~~~~~~~~~~

See `Requirements <https://ocp-software-handbook.readthedocs.io/en/latest/python/requirements.html>`__ in the OCP Software Development Handbook.

Update translations
~~~~~~~~~~~~~~~~~~~

#. Update the message catalogs:

   .. code-block:: bash

      pybabel extract -F babel.cfg -o messages.pot .
      pybabel update -N -i messages.pot -d locale

#. Compile the message catalogs (in development):

   .. code-block:: bash

      pybabel compile -f -d locale

.. note::

   The ``babel.cfg`` file lists from which ``StrEnum`` classes to extract messages. If Credere is deployed in English, we need to add an ``en`` locale to translate these. Otherwise, the translations will be database values like "MICRO", not "0 to 10".

.. admonition:: Reference

   The ``pybabel`` commands are from `Translate with Transifex <https://ocp-software-handbook.readthedocs.io/en/latest/python/i18n.html#translate-with-transifex>`__.

Update API
~~~~~~~~~~

.. seealso:: :doc:`../api/index`

Use the parameter ``id`` only for application IDs, to avoid accidental errors.

After making changes, regenerate the OpenAPI document by :ref:`running the server<dev-server>` and:

.. code-block:: bash

   curl http://localhost:8000/openapi.json -o docs/_static/openapi.json

Update models
~~~~~~~~~~~~~

Check whether a migration is needed:

.. code-block:: bash

   alembic check

If so, either auto-detect the changes made to ``models.py``, subject to `limitations <https://alembic.sqlalchemy.org/en/latest/autogenerate.html#what-does-autogenerate-detect-and-what-does-it-not-detect>`__:

.. code-block:: bash

   alembic revision --autogenerate -m "migration name"

Or, create a blank migration file:

.. code-block:: bash

   alembic revision -m "migration name"

Both generate a file like ``migrations/versions/2ca870aa737d_migration_name.py``. Edit the ``upgrade`` and ``downgrade`` functions, as needed.

.. tip::

   Need to undo your migration in development? Find the previous revision:

   .. code-block:: bash

      alembic history

   And revert, for example:

   .. code-block:: bash

      alembic downgrade 20e0ff589a61

Then, `update <https://ocp-software-handbook.readthedocs.io/en/latest/services/postgresql.html#generate-entity-relationship-diagram>`__ the :ref:`erd`. For example:

.. code-block:: bash

   java -jar schemaspy.jar -t pgsql -dp postgresql.jar -host localhost -db credere_backend -o schemaspy -norows -I '(django|auth).*'
   mv schemaspy/diagrams/orphans/orphans.png docs/_static/
   mv schemaspy/diagrams/summary/relationships.real.large.png docs/_static/

.. _erd:

Entity relationship diagram
---------------------------

.. image:: /_static/relationships.real.large.png
   :target: /_images/relationships.real.large.png

.. image:: /_static/orphans.png
   :target: /_images/orphans.png
