CloudFront
==========

CloudFront is used to serve images for emails.

.. attention:: If images are changed in git, the cache isn't invalidated! Read `Invalidate files to remove content <https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Invalidation.html>`__ for options.

.. tip:: Use CloudFront's *Reports & analytics* to check `Popular objects <https://us-east-1.console.aws.amazon.com/cloudfront/v3/home?region=us-east-1#/popular_urls>`__ and other statistics.

Configuration
-------------

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
