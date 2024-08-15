Commands
========

.. code-block:: bash

   python -m app.commands --help

.. _cmd-fetch-awards:

Fetch new awards
----------------

.. code-block:: bash

   python -m app.commands fetch-awards

This command gets new contracts since the last updated award date. For each new contract, an award is created, a borrower is either retrieved or created, and if the borrower has not declined opportunities, an application is created for them. An invitation email is sent to the borrower.

.. _cmd-remove-dated-application-data:

Remove user data from dated applications
----------------------------------------

.. code-block:: bash

   python -m app.commands remove-dated-application-data

Queries the applications in DECLINED, REJECTED, COMPLETED, and LAPSED status that have remained in these states longer than the time defined in the environment variable ``DAYS_TO_ERASE_BORROWERS_DATA``. If no other application is using the data, it deletes all the personal data of the borrower (name, email, address, legal identifier).

.. _cmd-update-applications-to-lapsed:

Set application status to lapsed
--------------------------------

.. code-block:: bash

   python -m app.commands update-applications-to-lapsed

Queries the applications in PENDING, ACCEPTED, and INFORMATION_REQUESTED status that have remained in these states longer than the time defined in the environment variable ``DAYS_TO_CHANGE_TO_LAPSED``, and changes their status to LAPSED.

.. _cmd-send-reminders:

Send mail reminders
-------------------

.. code-block:: bash

   python -m app.commands send-reminders

-  Queries the applications in PENDING status that fall within the range leading up to the expiration date. This range is defined by the environment variable ``REMINDER_DAYS_BEFORE_EXPIRATION``.

-  The intro reminder email is sent to the applications that fulfill the previous condition.

-  Queries the applications in ACCEPTED status that fall within the range leading up to the expiration date. This range is defined by the environment variable ``REMINDER_DAYS_BEFORE_EXPIRATION``.

-  The submit reminder email is sent to the applications that fulfill the previous condition.

.. _cmd-sla-overdue-applications:

Send overdue appliations emails to FI users
-------------------------------------------

.. code-block:: bash

   python -m app.commands sla-overdue-applications

This command identifies applications that are in INFORMATION_REQUESTED or STARTED status and overdue based on the lender's service level agreement (SLA). For each overdue application, an email is sent to OCP and to the respective lender. The command also updates the **overdued_at** attribute for applications that exceed the lender's SLA days.

.. _cmd-update-statistics:

Update statistics
-----------------

.. code-block:: bash

   python -m app.commands update-statistics

Performs the calculation needed to populate the statistic table with data from other tables, mainly, the Applications table.
