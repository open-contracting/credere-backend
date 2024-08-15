Simple Notification Service (SNS)
=================================

Configuration
-------------

Topics
~~~~~~

#. Access `Topics <https://us-east-1.console.aws.amazon.com/sns/v3/home?region=us-east-1#/topics>`__
#. Click the *Create topic* button

   -  **Type:** Check "Standard"
   -  **Name:** ``credere-noreply-open-contracting-org``

Subscriptions
~~~~~~~~~~~~~

#. Access `Subscriptions <https://us-east-1.console.aws.amazon.com/sns/v3/home?region=us-east-1#/subscriptions>`__
#. Click the *Create subscription* button

   -  **Topic ARN:** Select the topic you created
   -  **Protocol:** Email
   -  **Endpoint:** An administrator's email address

