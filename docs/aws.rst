Amazon Web Services (AWS)
=========================

There are two users:

-  An operational user, used by the application 
-  An administrative user, used by consultants

CloudFront
----------

CloudFront is used to serve images for emails.

General
  -  **Price class:** Use only North America and Europe (nearby region and lowest price)
  -  **Alternate domain name (CNAME):** cdn.credere.open-contracting.org
  -  **Custom SSL certificate:** Click *Request certificate*
  -  **Supported HTTP versions:** HTTP/2
  -  **Standard logging:** Off (requires S3)
  -  **IPv6:** On
Security
  Disabled
Origins
  -  **Origin domain:** credere.open-contracting.org
  -  **Protocol:** HTTPS only
  -  **Minumum Origin SSL protocol:** TLSv1.2
  -  **Enable Origin Shield:** No
Behaviors › Default (*)
  -  **Compress objects automatically:** No
  -  **Viewer protocol policy:** HTTPS only
  -  **Allowed HTTP methods:** GET, HEAD
  -  **Restrict viewer access:** No

  Cache policy and origin request policy
    - **Cache policy:** `CachingDisabled <https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-cache-policies.html#managed-cache-policy-caching-disabled>`__
    - **Origin request policy:** None

Then, create behaviors for the ``/*.jpg`` and ``/*.png`` paths with the same configuration, except with a *Cache policy* of `CachingOptimizedForUncompressedObjects <https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-cache-policies.html#managed-cache-caching-optimized-uncompressed>`__ (binary files are already compressed).

.. note:: `credere-frontend <https://github.com/open-contracting/credere-frontend>`__'s ``public`` directory also contains ``.avif``, ``.jpeg``, ``.svg`` and font files, but these are not referenced by email templates. Emails use the CDN, because they produce more traffic spikes.

.. attention:: If images are changed, the cache isn't invalidated! Read `Invalidate files to remove content <https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Invalidation.html>`__ for options.

.. tip:: Use CloudFront's *Reports & analytics* to check "Popular objects" and other statistics.

CloudWatch
----------

`Access our metrics. <https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#metricsV2?graph=~(view~'timeSeries~stacked~false~metrics~(~(~'AWS*2fSES~'Bounce)~(~'.~'Delivery)~(~'.~'Reputation.BounceRate)~(~'.~'Reputation.ComplaintRate)~(~'.~'Send))~region~'us-east-1~start~'-PT2160H~end~'P0D)&query=~'*7bAWS*2fSES*7d>`__

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

-  cognito-idp:AdminCreateUser
-  cognito-idp:AdminSetUserPassword
-  cognito-idp:AdminResetUserPassword
-  cognito-idp:AdminUpdateUserAttributes
-  cognito-idp:AdminInitiateAuth
-  cognito-idp:AdminUserGlobalSignOut

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
