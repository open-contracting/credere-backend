Deployment
==========

Before deploying the application, configure :doc:`../aws/index`.

After deploying the application, :ref:`cognito-admin` in AWS Cognito.

Environment variables
---------------------

COGNITO_CLIENT_ID
  your client id inside cognito
COGNITO_CLIENT_SECRET
  your client secret from cognito client app
AWS_ACCESS_KEY
  AWS key from the account that owns the users pool
AWS_CLIENT_SECRET
  AWS secret from the account that owns the users pool
AWS_REGION
  cognito and SES pool region
COGNITO_POOL_ID
  cognito pool id
EMAIL_SENDER_ADDRESS
  authorized sender in cognito
FRONTEND_URL
  frontend url, use http://localhost:3000/ for dev
SENTRY_DSN
  the DSN for sentry
COLOMBIA_SECOP_APP_TOKEN
  token to set header to fetch SECOP data
SECOP_PAGINATION_LIMIT
  page size to fetch SECOP data
SECOP_DEFAULT_DAYS_FROM_ULTIMA_ACTUALIZACION
  days used to compare field ultima_actualizacion the first time a fetching to SECOP data is made (or no awards in database)
HASH_KEY
  key for hashing identifiers for privacy concerns
APPLICATION_EXPIRATION_DAYS
  days to expire link after application creation
IMAGES_BASE_URL
  url where the images are served
IMAGES_LANG_SUBPATH
  static sub-path to IMAGES_BASE_URL containing the localized versions of the text in the images buttons.
FACEBOOK_LINK
  link to OCP Facebook account
TWITTER_LINK
  link to OCP Twitter account
LINK_LINK
  link to (Pending to define)
TEST_MAIL_RECEIVER
  email used to send invitations when fetching new awards or emails to borrower.
DAYS_TO_ERASE_BORROWERS_DATA
  the number of days to wait before deleting borrower data
DAYS_TO_CHANGE_TO_LAPSED
  the number of days to wait before changing the status of an application to 'Lapsed'
OCP_EMAIL_GROUP
  list of ocp users for notifications
MAX_FILE_SIZE_MB
  max file size allowed to be uploaded
TEST_DATABASE_URL
  Local test database in order to not drop and generate the main local database all the time
PROGRESS_TO_REMIND_STARTED_APPLICATIONS
  % of days of lender SLA before an overdue reminder, for example a lender with a SLA of 10 days will receive the first overdue at 7 days mark
ENVIRONMENT
  needs to be set as "production" in order to send emails to real borrower address. If not, emails will be sent to TEST_MAIL_RECEIVER
