Amazon Web Services (AWS)
=========================

There are two users:

-  An operational user, used by the application 
-  An administrative user, used by consultants

CloudWatch
----------

-  cloudwatch:ListMetrics
-  cloudwatch:GetMetricData

CloudWatch Logs
---------------

This builds on the `IAM policy example <https://docs.aws.amazon.com/step-functions/latest/dg/cw-logs.html#cloudwatch-iam-policy>`__:

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

-  cognito-idp:AdminCreateUser
-  cognito-idp:AdminSetUserPassword
-  cognito-idp:AdminResetUserPassword
-  cognito-idp:AdminUpdateUserAttributes
-  cognito-idp:AdminInitiateAuth
-  cognito-idp:AdminUserGlobalSignOut

The operational user has access to the development and production user pools. The administrative user has access to the development user pool only.

Simple Email Service (SES)
--------------------------

Configuration sets
~~~~~~~~~~~~~~~~~~

This follows `Monitor email sending using Amazon SES event publishing <https://docs.aws.amazon.com/ses/latest/dg/monitor-using-event-publishing.html>`__:

-  Configuration sets (`Step 1 <https://docs.aws.amazon.com/ses/latest/dg/event-publishing-create-configuration-set.html>`__)

   -  ses:ListConfigurationSets (*added*)
   -  ses:GetConfigurationSet (*added*)
   -  ses:CreateConfigurationSet
   -  ses:DeleteConfigurationSet (*added*)
   -  ses:TagResource (required to create configuration set)

-  Destinations (`Step 2 <https://docs.aws.amazon.com/ses/latest/dg/event-publishing-add-event-destination-cloudwatch.html>`__, linking to `permissions <https://docs.aws.amazon.com/ses/latest/dg/event-destinations-manage.html>`__)

   -  ses:GetConfigurationSetEventDestinations (*added*)
   -  ses:CreateConfigurationSetEventDestination
   -  ses:UpdateConfigurationSetEventDestination
   -  ses:DeleteConfigurationSetEventDestination

Safe permissions
~~~~~~~~~~~~~~~~

-  ses:ListTemplates
-  ses:GetTemplate
-  ses:TestRenderTemplate

Unsafe permissions
~~~~~~~~~~~~~~~~~~

-  ses:SendEmail
-  ses:SendRawEmail

These are constrained to ``credere-*`` templates, the ``credere`` configuration set and the ``credere@noreply.open-contracting.org`` identity:

-  ses:SendTemplatedEmail
-  ses:SendBulkTemplatedEmail

The administrative user also has:

-  ses:CreateTemplate
-  ses:UpdateTemplate
-  ses:DeleteTemplate

Simple Storage Services (S3)
----------------------------

These are contrained to the ``ocp-credere`` bucket and its resources:

-  s3:ListBucket
-  s3:PutObject
-  s3:GetObject
-  s3:DeleteObject
