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
