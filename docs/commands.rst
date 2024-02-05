Commands
========

.. code-block:: bash

   python -m app.commands --help

Fetch new awards
----------------

.. code-block:: bash

   python -m app.commands fetch-awards

This command gets new contracts since the last updated award date. For each new contract, an award is created, a borrower is either retrieved or created, and if the borrower has not declined opportunities, an application is created for them. An invitation email is sent to the borrower (or the test email, depending on env variables *ENVIRONMENT* and *TEST_MAIL_RECEIVER* values).

Remove user data from dated applications
----------------------------------------

.. code-block:: bash

   python -m app.commands remove-dated-application-data

Queries the applications in ‘declined’, ‘rejected’, ‘completed’, and ‘lapsed’ status that have remained in these states longer than the time defined in the environment variable *DAYS_TO_ERASE_BORROWERS_DATA*. If no other application is using the data, it deletes all the personal data of the borrower (name, email, address, legal identifier).”

Set application status to lapsed
--------------------------------

.. code-block:: bash

   python -m app.commands update-applications-to-lapsed

Queries the applications in ‘PENDING’, ‘ACCEPTED’, and ‘INFORMATION\ *REQUESTED’ status that have remained in these states longer than the time defined in the environment variable \_DAYS_TO_CHANGE_TO_LAPSED*, and changes their status to ’LAPSED’.

Send mail reminders
-------------------

.. code-block:: bash

   python -m app.commands send-reminders

-  Queries the applications in ‘PENDING’ status that fall within the range leading up to the expiration date. This range is defined by the environment variable *REMINDER_DAYS_BEFORE_EXPIRATION*.

-  The intro reminder email is sent to the applications that fulfill the previous condition.

-  Queries the applications in ‘ACCEPTED’ status that fall within the range leading up to the expiration date. This range is defined by the environment variable *REMINDER_DAYS_BEFORE_EXPIRATION*.

-  The submit reminder email is sent to the applications that fulfill the previous condition.

Send overdue appliations emails to FI users
-------------------------------------------

.. code-block:: bash

   python -m app.commands sla-overdue-applications

This command identifies applications that are in ‘INFORMATION_REQUESTED’ or ‘STARTED’ status and overdue based on the lender’s service level agreement (SLA). For each overdue application, an email is sent to OCP and to the respective lender. The command also updates the **overdued_at** attribute for applications that exceed the lender’s SLA days.

Update statistics
-----------------

.. code-block:: bash

   python -m app.commands update-statistics

Performs the calculation needed to populate the statistic table with data from other tables, mainly, the Applications table.

Statistics updates
~~~~~~~~~~~~~~~~~~

This process is automatically run every time a user or MSME action adds new data that affects the statistics. The enpoints that update statistics are:

-  ``POST /applications/access-scheme``
-  ``POST /applications/{id}/reject-application``
-  ``POST /applications/{id}/complete-application``
-  ``POST /applications/{id}/approve-application``
-  ``POST /applications/{id}/start``
-  ``POST /applications/confirm-credit-product``
-  ``POST /applications/submit``
-  ``POST /applications/email-sme/``
-  ``POST /applications/complete-information-request``
-  ``POST /applications/decline``
-  ``POST /applications/rollback-decline``
-  ``POST /applications/decline-feedback``
