SQLAlchemy
==========

Read SQLAlchemy's `Session Basics <https://docs.sqlalchemy.org/en/20/orm/session_basics.html>`__, in particular:

-  `Adding New or Existing Items <https://docs.sqlalchemy.org/en/20/orm/session_basics.html#adding-new-or-existing-items>`__

      "For transient (i.e. brand new) instances, ``Session.add()`` will have the effect of an INSERT taking place for those instances upon the next flush. For instances which are persistent (i.e. were loaded by this session), they are already present and do not need to be added."

-  `Flushing <https://docs.sqlalchemy.org/en/20/orm/session_basics.html#session-flushing>`__

      With ``autoflush=True``, "the flush step is nearly always done transparently. Specifically, the flush occurs before any individual SQL statement is issued as a result of a ``Query`` …, as well as within the ``Session.commit()`` call before the transaction is committed."

-  `When do I construct a Session, when do I commit it, and when do I close it? <https://docs.sqlalchemy.org/en/20/orm/session_basics.html#when-do-i-construct-a-session-when-do-i-commit-it-and-when-do-i-close-it>`__

      For web applications, "the basic pattern is create a ``Session`` at the start of a web request, call the ``Session.commit()`` method at the end of web requests that do POST, PUT, or DELETE, and then close the session at the end of web request"

-  `Expiring / Refreshing <https://docs.sqlalchemy.org/en/20/orm/session_basics.html#expiring-refreshing>`__ (also under `State Management <https://docs.sqlalchemy.org/en/20/orm/session_state_management.html#refreshing-expiring>`__, in particular, `When to Expire or Refresh <https://docs.sqlalchemy.org/en/20/orm/session_state_management.html#when-to-expire-or-refresh>`__)

   In SQLAlchemy, `as SQLModel documents <https://sqlmodel.tiangolo.com/tutorial/automatic-id-none-refresh/#commit-the-changes-to-the-database>`__, if you access an instance (but not its attributes) after ``session.commit()`` – like when constructing a JSON response – then "something unexpected happens" by default. We follow the advice from the answer to the previous question:

      "It’s also usually a good idea to set ``Session.expire_on_commit`` to False so that subsequent access to objects that came from a ``Session`` within the view layer do not need to emit new SQL queries to refresh the objects, if the transaction has been committed already."


   .. seealso:: `I’m re-loading data with my Session but it isn’t seeing changes that I committed elsewhere <https://docs.sqlalchemy.org/en/20/faq/sessions.html#i-m-re-loading-data-with-my-session-but-it-isn-t-seeing-changes-that-i-committed-elsewhere>`__

-  `My Query does not return the same number of objects as query.count() tells me - why? <https://docs.sqlalchemy.org/en/20/faq/sessions.html#my-query-does-not-return-the-same-number-of-objects-as-query-count-tells-me-why>`__

Flushing
--------

-  Use ``session.add(instance)`` to INSERT rows.
-  Use ``instance.related = related``, not ``instance.related_id = related.id``.

   .. attention::

      Otherwise, if ``session.flush()`` is not called after ``session.add(related)``, then ``related.id`` is ``None``!

-  Use the :meth:`app.models.ActiveRecordMixin.create` and :meth:`app.models.ActiveRecordMixin.update` methods, which call ``session.flush()`` to avoid such errors.

Committing
----------

-  Credere is an email-centered service. Until an email is sent, processing is incomplete. Send emails after all database queries (other than ``Message`` creation, which depends on the message ID), *then* commit. That way, after emails are sent, only integrity errors could cause the transaction to rollback (unfortunately, sent emails can't be undone).
-  Commit before adding `background tasks <https://fastapi.tiangolo.com/reference/background/?h=background>`__ and returning responses, to ensure changes are persisted before irreversible actions are taken.
-  In a for-loop, commit after sending an email, so that if a later query fails, we don't send repeat emails on the next run. This is contrary to the advice in `Session Basics <https://docs.sqlalchemy.org/en/20/orm/session_basics.html#when-do-i-construct-a-session-when-do-i-commit-it-and-when-do-i-close-it>`__:

      "For a command-line script, the application would create a single, global ``Session`` that is established when the program begins to do its work, and **commits it right as the program is completing its task**." (emphasis added)

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
