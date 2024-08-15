Simple Email Service (SES)
==========================

Configuration
-------------

Configuration sets
~~~~~~~~~~~~~~~~~~

#. Access `Configuration sets <https://us-east-1.console.aws.amazon.com/ses/home?region=us-east-1#/configuration-sets>`__
#. Click the *Create set* button

   -  **Configuration set name**: ``credere``

#. Click the *Event destinations* tab
#. Click the *Add destination* button

   .. tab-set::

      .. tab-item:: CloudWatch

         .. seealso:: :doc:`cloudwatch`

         Select event types
            -  **Sending and delivery:** Check all
         Specify destination
            -  **Destination type:** Check "Amazon CloudWatch"
            -  **Name:** ``crede-metrics-to-cloudwatch``
            -  **Value source:** Select "Message tag"
            -  **Dimension name:** ``ses:configuration-set``
            -  **Default value:** ``crede-metrics-to-cloudwatch`` (*sic*)

      .. tab-item:: Simple Notification Service

         .. seealso:: :doc:`sns`

         Select event types
            - **Sending and delivery:** Check:
               -  Rendering failures
               -  Rejects
               -  Delivery delays
         Specify destination
            -  **Destination type:** Check "Amazon SNS"
            -  **Name:** ``credere-noreply-open-contracting-org``
            -  **SNS topic:** ``credere-noreply-open-contracting-org``

.. seealso:: `Set up advanced notifications <https://ocdsdeploy.readthedocs.io/en/latest/deploy/aws.html#set-up-advanced-notifications>`__

Identities
~~~~~~~~~~

#. `Verify an email address <https://ocdsdeploy.readthedocs.io/en/latest/deploy/aws.html#verify-an-email-address>`__ (``credere@noreply.open-contracting.org``)

   Authentication
      -  `Use a MAIL FROM domain <https://ocdsdeploy.readthedocs.io/en/latest/deploy/aws.html#use-a-mail-from-domain>`__
   Notifications
      - Set the bounce and complaint feedback to the :doc:`sns` topic
      - Check "Include original email headers" for both
   Configuration set
      - Assign ``credere`` as the default configuration set

.. seealso:: `Set up basic notifications <https://ocdsdeploy.readthedocs.io/en/latest/deploy/aws.html#set-up-basic-notifications>`__
