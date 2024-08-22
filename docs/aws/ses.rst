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
            -  **Name:** ``crede-metrics-to-cloudwatch`` (*sic*)
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

Email templates
~~~~~~~~~~~~~~~

.. admonition:: One-time setup

   #. `Install the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html>`__
   #. Run the `configure <https://docs.aws.amazon.com/cli/latest/reference/configure/>`__ command to set the :doc:`administrative user<iam>`'s credentials and region:

      .. code-block:: bash

         aws configure --profile credere-admin

The files matching the pattern ``email_templates/aws_*`` are used as `email templates <https://docs.aws.amazon.com/ses/latest/dg/send-personalized-email-api.html>`__. They serve as layouts for all messages, including styles, a header, a footer, and a ``{{CONTENT}}`` tag.

-  ``aws_main.html``
-  ``aws_main_es.html``

When deploying for the first time, and after changing these files:

#. Create the input JSON for each template:

   .. code-block:: bash

      python -m app dev cli-input-json credere-main-en email_templates/aws_main.html > credere-main-en.json
      python -m app dev cli-input-json credere-main-es email_templates/aws_main_es.html > credere-main-es.json

#. Run the `ses create-template <https://docs.aws.amazon.com/cli/latest/reference/ses/create-template.html>`__ command with the administrative user:

   .. code-block:: bash

      aws ses create-template --profile credere-admin --cli-input-json file://credere-main-en.json
      aws ses create-template --profile credere-admin --cli-input-json file://credere-main-es.json

Tasks
-----

Get an email template
~~~~~~~~~~~~~~~~~~~~~

Use the CLI (the `console <https://us-east-1.console.aws.amazon.com/ses/home?region=us-east-1#/email-templates>`__ only lists templates):

.. code-block:: bash

   aws ses get-template --profile credere-admin --template-name credere-main-es

Preview a templated email
~~~~~~~~~~~~~~~~~~~~~~~~~

#. Create an input JSON file, using the skeleton from:

   .. code-block:: bash

      aws ses test-render-template --generate-cli-skeleton

   For example:

   .. code-block:: json

      {
        "TemplateName": "credere-main-es",
        "TemplateData": "{\"SUBJECT\":\"my subject\",\"CONTENT\":\"my content\"}"
      }

#. Run the `ses test-render-template <https://docs.aws.amazon.com/cli/latest/reference/ses/test-render-template.html>`__ command, for example:

   .. code-block:: bash

      aws ses test-render-template --profile credere-admin --cli-input-json file://test.json

Send a templated email
~~~~~~~~~~~~~~~~~~~~~~

#. Create an input JSON file, using the skeleton from:

   .. code-block:: bash

      aws ses send-templated-email --generate-cli-skeleton

   For example:

   .. code-block:: json

      {
        "Source": "Credere_Test <credere@noreply.open-contracting.org>",
        "Destination": {
          "ToAddresses": ["me@open-contracting.org"]
        },
        "ReplyToAddresses": ["test@open-contracting.org"],
        "Template": "credere-main-es",
        "TemplateData": "{\"SUBJECT\":\"my subject\",\"CONTENT\":\"my content\"}"
      }

#. Run the `ses send-templated-email <https://docs.aws.amazon.com/cli/latest/reference/ses/send-templated-email.html>`__ command, example:

   .. code-block:: bash

      aws ses send-templated-email --profile credere-admin --cli-input-json file://test.json
