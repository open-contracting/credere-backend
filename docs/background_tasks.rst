Background tasks
================

To run the list of commands available use

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

-  post “/applications/access-scheme”
-  post “/applications/{id}/reject-application”,
-  post “/applications/{id}/complete-application”,
-  post “/applications/{id}/approve-application”,
-  post “/applications/{id}/start”
-  post “/applications/confirm-credit-product”,
-  post “/applications/submit”
-  post “/applications/email-sme/”
-  post “/applications/complete-information-request”
-  post “/applications/decline”
-  post “/applications/rollback-decline”,
-  post “/applications/decline-feedback”

Cron
----

The background processes are set to run as cron jobs in the server. You can configure this using:

.. code-block:: bash

   crontab -e

Sample crontab configuration:

.. code-block:: none

   0 4 * * * /usr/bin/docker exec credere-backend-1 python -m app.commands fetch-awards >> /dev/null 2>&1
   0 5 * * * /usr/bin/docker exec credere-backend-1 python -m app.commands remove-dated-application-data >> /dev/null 2>&1
   0 6 * * * /usr/bin/docker exec credere-backend-1 python -m app.commands update-applications-to-lapsed >> /dev/null 2>&1
   0 7 * * * /usr/bin/docker exec credere-backend-1 python -m app.commands send-reminders >> /dev/null 2>&1
   0 8 * * * /usr/bin/docker exec credere-backend-1 python -m app.commands sla-overdue-applications >> /dev/null 2>&1
   0 6 * * * /usr/bin/docker exec credere-backend-1 python -m app.commands update-statistics >> /dev/null 2>&1
