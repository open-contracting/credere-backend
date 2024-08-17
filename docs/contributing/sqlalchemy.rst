SQLAlchemy
==========

Reminders
---------

-  Use ``instance.related = related``, not ``instance.related_id = related.id``. If ``session.flush()`` was not called ``session.add(related)``, then ``related.id`` is ``None``.

Query API
---------

Use the `Legacy Query API <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html>`__. (The project started with SQLAlchemy 1.4. `2.0 syntax <https://docs.sqlalchemy.org/en/20/changelog/migration_20.html#migration-20-query-usage>`__ is more verbose.)

SELECT
~~~~~~

When selecting specific columns (like ``session.query(models.MyModel.field)``), if the query is in a…

-  For-loop, do, for example:

   .. code-block:: python

      for (lender_id,) in session.query(models.Lender.id):
          print(lender_id)

   or:

   .. code-block:: python

      for name, value in session.query(...):
          print(name, value)

   NOT:

   .. code-block:: python

      for row in session.query(models.Lender.id):  # AVOID
          print(row[0])

-  If-statement, do, for example:

   .. code-block:: python

      if lender_id := session.query(models.Lender.id).limit(1).scalar():
          print(lender_id)

   NOT:

   .. code-block:: python

      if row := session.query(models.Lender.id).first(): # AVOID
          print(row[0])

.. tip::

   Maintainers can find queries for specific columns using the regular expression:

   .. code-block:: none

      session.query\((models\.\w+\.|(?!models)\w+\.)

JOIN
~~~~

-  To join the ``Award`` model, always explicitly use ``join(Award, Award.id == Application.award_id)``, because we want to count applications or borrowers only. We don't want to count awards, like with ``join(Award, Award.borrower_id == Borrower.id)``.
-  To join another model, use ``join(model)``, not ``join(model, model.… == other.…)``. If an ON clause is needed, use the order ``join(model, model.… == other.…)``, not ``join(model, other.… == model.…)``.

WHERE
~~~~~

-  Use `filter <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.filter>`__, not `filter_by <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.filter_by>`__, to avoid ambiguity.
-  Use ``filter(a, b, c)``, not ``filter(a).filter(b).filter(c)``.

Chains
~~~~~~

``Query`` instance methods can be chained **in any order**, but typically:

-  `distinct <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.distinct>`__
-  `join <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.join>`__

   .. note:: "the order in which each call to the join() method occurs is important."

-  `outerjoin <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.outerjoin>`__
-  `options <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.options>`__, with `joinedload <https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html#sqlalchemy.orm.joinedload>`__ or `defaultload <https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html#sqlalchemy.orm.defaultload>`__
-  `filter <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.filter>`__, not `where <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.where>`__
-  `group_by <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.group_by>`__
-  `having <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.having>`__
-  `order_by <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.order_by>`__
-  `limit <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.limit>`__
-  `offset <https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.offset>`__

Execution
~~~~~~~~~

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

.. attention:: Do not use a query in a condition, without executing it! ``bool(query)`` returns ``True`` even if the result would be empty.

.. seealso:: `My Query does not return the same number of objects as query.count() tells me - why? <https://docs.sqlalchemy.org/en/20/faq/sessions.html#faq-query-deduplicating>`__
