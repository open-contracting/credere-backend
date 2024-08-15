Identity and Access Management (IAM)
====================================

There are two users:

-  An operational user, used by the application 
-  An administrative user, used by consultants

CloudWatch
----------

Safe permissions
~~~~~~~~~~~~~~~~

Only the administrative user has these.

-  cloudwatch:ListMetrics
-  cloudwatch:GetMetricData

CloudWatch Logs
---------------

Only the administrative user has these. This builds on the `IAM policy example <https://docs.aws.amazon.com/step-functions/latest/dg/cw-logs.html#cloudwatch-iam-policy>`__:

-  Log groups

   -  logs:CreateLogGroup (*added*)
   -  logs:DescribeLogGroups
   -  logs:DeleteLogGroup (*added*)

-  Log streams

   -  logs:CreateLogStream
   -  logs:DescribeLogStreams (*added*)
   -  logs:DeleteLogStream (*added*)

-  Log deliveries

   -  logs:CreateLogDelivery
   -  logs:ListLogDeliveries
   -  logs:GetLogDelivery
   -  logs:UpdateLogDelivery
   -  logs:DeleteLogDelivery

-  Log events

   -  logs:PutLogEvents
   -  logs:GetLogEvents (*added*)
   -  logs:FilterLogEvents (*added*)

-  Resource policies

   -  logs:PutResourcePolicy
   -  logs:DescribeResourcePolicies
   -  logs:DeleteResourcePolicy (*added*)

.. seealso::

   `Actions defined by Amazon CloudWatch Logs <https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazoncloudwatchlogs.html#amazoncloudwatchlogs-actions-as-permissions>`__

Cognito
-------

The operational user has access to the development and production user pools. The administrative user has access to the development user pool only. All permissions are unsafe.

-  cognito-idp:AdminCreateUser (``admin_create_user`` in boto3)
-  cognito-idp:AdminSetUserPassword (``admin_set_user_password`` in boto3)
-  cognito-idp:AdminResetUserPassword (for testing and troubleshooting)
-  cognito-idp:AdminUpdateUserAttributes (``admin_update_user_attributes`` in boto3)
-  cognito-idp:AdminInitiateAuth (for testing and troubleshooting)
-  cognito-idp:AdminUserGlobalSignOut (``admin_user_global_sign_out`` in boto3)

.. note::

   The Cognito client also uses these boto3 methods, but the :doc:`app client<cognito>` has permission already:

   - ``initiate_auth`` (cognito-idp:InitiateAuth)
   - ``respond_to_auth_challenge`` (cognito-idp:RespondToAuthChallenge)
   - ``associate_software_token`` (cognito-idp:AssociateSoftwareToken)
   - ``verify_software_token`` (cognito-idp:VerifySoftwareToken)
   - ``get_user`` (cognito-idp:GetUser)

Simple Email Service (SES)
--------------------------

Configuration sets
~~~~~~~~~~~~~~~~~~

Only the administrative user has these.

Safe permissions
^^^^^^^^^^^^^^^^

-  ses:ListConfigurationSets
-  ses:GetConfigurationSet
-  ses:GetConfigurationSetEventDestinations

Unsafe permissions
^^^^^^^^^^^^^^^^^^

This follows `Monitor email sending using Amazon SES event publishing <https://docs.aws.amazon.com/ses/latest/dg/monitor-using-event-publishing.html>`__:

-  Configuration sets (`Step 1 <https://docs.aws.amazon.com/ses/latest/dg/event-publishing-create-configuration-set.html>`__)

   -  ses:CreateConfigurationSet
   -  ses:DeleteConfigurationSet (*added*)
   -  ses:TagResource (*added*, required to create configuration set)

-  Destinations (`Step 2 <https://docs.aws.amazon.com/ses/latest/dg/event-publishing-add-event-destination-cloudwatch.html>`__, linking to `permissions <https://docs.aws.amazon.com/ses/latest/dg/event-destinations-manage.html>`__)

   -  ses:CreateConfigurationSetEventDestination
   -  ses:UpdateConfigurationSetEventDestination
   -  ses:DeleteConfigurationSetEventDestination

Templates
~~~~~~~~~

Safe permissions
^^^^^^^^^^^^^^^^

Both users have:

-  ses:ListTemplates
-  ses:GetTemplate
-  ses:TestRenderTemplate

Unsafe permissions
^^^^^^^^^^^^^^^^^^

Only the administrative user has:

-  ses:CreateTemplate
-  ses:UpdateTemplate
-  ses:DeleteTemplate

Sending
~~~~~~~

Unsafe permissions
^^^^^^^^^^^^^^^^^^

Both users have:

-  ses:SendEmail
-  ses:SendRawEmail

Both users have these, which are constrained to ``credere-*`` templates, the ``credere`` configuration set and the ``credere@noreply.open-contracting.org`` identity:

-  ses:SendTemplatedEmail
-  ses:SendBulkTemplatedEmail
