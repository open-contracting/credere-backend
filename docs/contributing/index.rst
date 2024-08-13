Contributing
============

Setup
-----

Install requirements:

.. code-block:: bash

   pip install -r requirements_dev.txt

If requirements are updated, re-run this command.

Install the git pre-commit hooks:

.. code-block:: bash

   pre-commit install

Create a ``.env`` file, using ``.envtest`` as an example.

Create development and test databases in PostgreSQL, and set the ``DATABASE_URL`` and ``TEST_DATABASE_URL`` environment variables, for example:

.. code-block:: bash

   DATABASE_URL=postgresql://{username}:{password}@{host_adress:port}/{db_name}

Run database migrations:

.. code-block:: bash

   alembic upgrade head

Tasks
-----

Update requirements
~~~~~~~~~~~~~~~~~~~

See `Requirements <https://ocp-software-handbook.readthedocs.io/en/latest/python/requirements.html>`__ in the OCP Software Development Handbook.

Run application
~~~~~~~~~~~~~~~

.. code-block:: bash

   uvicorn app.main:app --reload

Run tests
~~~~~~~~~

The ``DATABASE_URL`` and ``TEST_DATABASE_URL`` environment variables must be set to the test database.

.. code-block:: bash

   pytest -W error

Check coverage:

.. code-block:: bash

   pytest --cov

Generate coverage HTML report:

.. code-block:: bash

   coverage html

You can the open ``htmlcov/index.html`` in a browser.

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

.. admonition:: One-time setup

   pip install furo sphinx-autobuild

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

Conventions
-----------

Black formater extention for VS code is being used for formatting, no config needed (ext id ms-python.black-formatter)

Settings configured according to `Fastapi guidelines <https://fastapi.tiangolo.com/advanced/settings/>`__

Versioning will be handled using an environment variable in .env file and following https://semver.org/

Follow `these conventions <https://ocp-software-handbook.readthedocs.io/en/latest/git/index.html>`__ for commit messages and branch names.

SQLAlchemy Query API
~~~~~~~~~~~~~~~~~~~~

Syntax
^^^^^^

-  Use the `Legacy Query API <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html>`__. This project started with SQLAlchemy 1.4. It has not migrated to `2.0 syntax <https://docs.sqlalchemy.org/en/20/changelog/migration_20.html#migration-20-query-usage>`__, which is more verbose.
-  Use `filter <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.filter>`__, instead of `filter_by <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.filter_by>`__, to avoid ambiguity.

Cheatsheet
^^^^^^^^^^

``Query`` instance methods can be chained **in any order**, but typically:

-  `distinct <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.distinct>`__
-  `join <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.join>`__

   .. note:: "the order in which each call to the join() method occurs is important."

-  `outerjoin <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.outerjoin>`__
-  `options <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.options>`__ with `joinedload <https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html#sqlalchemy.orm.joinedload>`__ or `defaultload <https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html#sqlalchemy.orm.defaultload>`__
-  `filter <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.filter>`__, not `where <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.where>`__
-  `group_by <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.group_by>`__
-  `having <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.having>`__
-  `order_by <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.order_by>`__
-  `limit <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.limit>`__
-  `offset <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.offset>`__

``Query`` instances must be executed with one of:

-  SELECT

   -  ``__iter__``
   -  `all <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.all>`__: all rows as ``list``
   -  `first <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.first>`__: at most one row
   -  `one <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.one>`__: exactly one row, or error
   -  `scalar <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.scalar>`__: the first column of `one_or_none <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.one_or_none>`__
   -  `count <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.count>`__: row count as ``int``

   .. attention: `exists() <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.exists>`__, unlike the Django ORM, doesn't execute the query.

-  `update <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.update>`__
-  `delete <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.delete>`__

.. attention:: `My Query does not return the same number of objects as query.count() tells me - why? <https://docs.sqlalchemy.org/en/20/faq/sessions.html#faq-query-deduplicating>`__

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

Deployment
----------

First admin user set up
~~~~~~~~~~~~~~~~~~~~~~~

#. Create a user in Cognito

   -  Create the user manually in the pool from the AWS console.
   -  Mark “Don’t send invitation” and mark the option of verified email address.
   -  After adding the new user to the pool, get the username from Cognito.

#. Create the user in the Credere database

   Insert in the user table from the Credere database a record for the user.

   .. code-block:: none

      INSERT INTO public.credere_user(type, language, email, name, external_id) VALUES (“OCP”, “es”, {EMAIL}, “Admin User”, {COGNITO_USER_ID});

#. Reset the password through the Frontend

   -  Go to the login page
   -  Click “Forgot Password?”
   -  You will receive the email to set the password and after that configure the MFA for the new user.
