# Credere Backend

## Basic setup runnig the app

First create a docker image with the following command:

```
docker build -t {image_name} .
```

After that you can run it using the following command or docker interface

```
docker run -d --name {container_name} -p 8000:8000 {image_name}
```

Changes may require you to re create the image, in that case delete it using:

```
docker rmi <your-image-id>
```

## Basic setup for development

First create an env with virtualenv, then activate and this the following command inside the virtual environment:

```
pip install -r requirements.txt
pip install -r requirements_dev.txt
```

Requirement files are created according to [OCP guidelines](https://ocp-software-handbook.readthedocs.io/en/latest/python/requirements.html)

`requirements.txt` and `requirements_dev.txt` should be included.
If you need to recreate or to update them you can run:

```
pip-compile
pip-compile requirements_dev.in
```

This will generate the files anew with all proper modules

For testing purposes you can run the app inside a virtual env using:

```
uvicorn app.main:app --reload
```

.env file needs to be created with the proper environment variables

you can use .envtest as an example, it has the following keys:

- COGNITO_CLIENT_ID -> your client id inside cognito
- COGNITO_CLIENT_SECRET -> your client secret from cognito client app
- AWS_ACCESS_KEY -> AWS key from the account that owns the users pool
- AWS_CLIENT_SECRET -> AWS secret from the account that owns the users pool
- AWS_REGION -> cognito and SES pool region
- COGNITO_POOL_ID -> cognito pool id
- EMAIL_SENDER_ADDRESS -> authorized sender in cognito
- FRONTEND_URL -> frontend url, use http://localhost:3000/ for dev
- SENTRY_DNS -> the DNS for sentry
- COLOMBIA_SECOP_APP_TOKEN -> token to set header to fetch SECOP data
- SECOP_PAGINATION_LIMIT -> page size to fetch SECOP data
- SECOP_DEFAULT_DAYS_FROM_ULTIMA_ACTUALIZACION -> days used to compare field ultima_actualizacion the first time a fetching to SECOP data is made (or no awards in database)
- HASH_KEY -> key for hashing identifiers for privacy concerns
- APPLICATION_EXPIRATION_DAYS -> days to expire link after application creation
- IMAGES_BASE_URL -> url where the images are served
- IMAGES_LANG_SUBPATH -> static sub-path to IMAGES_BASE_URL containing the localized versions of the text in the images buttons.
- FACEBOOK_LINK -> link to OCP Facebook account
- TWITTER_LINK -> link to OCP Twitter account
- LINK_LINK -> link to (Pending to define)
- TEST_MAIL_RECEIVER -> email used to send invitations when fetching new awards or emails to borrower.
- DAYS_TO_ERASE_BORROWERS_DATA -> the number of days to wait before deleting borrower data
- DAYS_TO_CHANGE_TO_LAPSED -> the number of days to wait before changing the status of an application to 'Lapsed'
- OCP_EMAIL_GROUP -> list of ocp users for notifications
- MAX_FILE_SIZE_MB -> max file size allowed to be uploaded
- PROGRESS_TO_REMIND_STARTED_APPLICATIONS -> % of days of lender SLA before an overdue reminder, for example a lender with a SLA of 10 days will receive the first overdue at 7 days mark
- ENVIRONMENT -> needs to be set as "production" in order to send emails to real borrower address. If not, emails will be sent to TEST_MAIL_RECEIVER

You should configure the pre-commit for the repo one time

```
pre-commit install
```

## Development process

### Identation and formatting

Black formater extention for VS code is being used for formatting, no config needed (ext id ms-python.black-formatter)

Settings configured according to [Fastapi guidelines](https://fastapi.tiangolo.com/advanced/settings/)

Versioning will be handled using an environment variable in .env file and following https://semver.org/

### API endpoints naming conventions

Use lowercase letters and separate words with hyphens or underscores.

> Example: GET /users or GET /users/all

If the endpoint retrieves a specific resource, use the resource name in its singular form.

> Example: GET /user/{id} or PUT /user/{id}

For endpoints that return collections of resources, use plural nouns.

> Example: GET /users or POST /users

Use sub-resources to represent relationships between resources.

> Example: GET /users/{id}/orders or GET /users/{id}/invoices

For actions or operations that do not fit into the RESTful resource model, consider using verbs or descriptive phrases.

> Example: POST /users/{id}/reset-password or PUT /users/{id}/activate

Avoid using abbreviations or acronyms unless they are widely understood and agreed upon within your development team or industry.

Ensure that the endpoint names are self-explanatory and reflect the purpose of the API operation.

## Branching, commits and PRs

Follow [these conventions](https://ocp-software-handbook.readthedocs.io/en/latest/git/index.html) for commit messages and branch names.

Before creating a pull request you can run a pre commit build in order to check for errors

Used the installed pre-commit config using the following command:

```
pre-commit run
```

## Postgress, migrations and changes in tables

You need to have a postgresql service running. You can either install postgres for windows or run the proper packaging in Linux cmd

Once you have the service you need to create a database

then you can set the env variable like this

```
DATABASE_URL=postgresql://{username}:{password}@{host_adress:port}/{db_name}
```

in order to apply migrations in tables use

```
alembic upgrade head
```

This will apply the migrations in your database

If you need to create a new migration you can use

```
alembic revision -m "migration name"
```

this will generate a file with a identifier and the name you picked.
It will look like this _2ca870aa737d_migration_name.py_

Inside the script you need to configure both operations, upgrade and downgrade. Upgrade will apply changes and downgrade remove them. Use the first migration as base.

Another option is to use

```
alembic revision --autogenerate -m "migration name"
```

This will attempt to auto-detect the changes made to schema.core.py and complete the upgrade and downgrade automatically.
This feature needs to be re-checked by the developer to ensure all changes were included. For more details on what is auto-detected, you can read the following link

https://alembic.sqlalchemy.org/en/latest/autogenerate.html#what-does-autogenerate-detect-and-what-does-it-not-detect

## Test

To run test locally

```
pytest tests -W error
```

## Run background jobs

To run the list of commands available use

```
python -m app.commands --help
```

### Command to fetch new awards is

```
python -m app.commands fetch-awards
```

It will send invitations to the email configure in the env variable _TEST_MAIL_RECEIVER_. Alternative could receive a custom email destination with **--email-invitation** argument

does the followings actions

- fetch application data from Secop and store it into the Credere database

- Send the invitation intro mail to the potential borrowers

```
python -m app.commands fetch-awards --email-invitation test@example.com
```

### Command to remove data from dated completed, declined, rejected and lapsed applications

```
python -m app.commands remove-dated-application-data
```

Queries the applications in 'declined', 'rejected', 'completed', and 'lapsed' status that have remained in these states longer than the time defined in the environment variable DAYS_TO_ERASE_BORROWERS_DATA. If no other application is using the data, it deletes all the personal data of the borrower (name, email, address, legal identifier)."

#### Scheduled Execution (Cron)

This process should be run once a day.

### Command to set application status to lapsed

```
python -m app.commands update-applications-to-lapsed

```

Queries the applications in 'pending', 'accepted', and 'requested' status that have remained in these states longer than the time defined in the environment variable DAYS_TO_CHANGE_TO_LAPSED, and changes their status to 'LAPSED'.

#### Scheduled Execution (Cron)

This process should be run once a day to keep the application's status updated.

### The command to send mail reminders is

```
python -m app.commands send-reminders
```

- Queries the applications in 'pending' status that fall within the range leading up to the expiration date. This range is defined by the environment variable REMINDER_DAYS_BEFORE_EXPIRATION.
- The intro reminder email is sent to the applications that fulfill the previous condition

- Queries the applications in 'accepted' status that fall within the range leading up to the expiration date. This range is defined by the environment variable REMINDER_DAYS_BEFORE_EXPIRATION.
- The submit reminder email is sent to the applications that fulfill the previous condition

#### Scheduled Execution (Cron)

This process should be run once a day.

### Command to send overdue appliations emails to FI users is

```
python -m app.commands sla-overdue-applications
```

### Command to update statistics is

```
python -m app.commands update-statistics
```

"Performs the calculation needed to populate the statistic table with data from other tables, mainly, the Applications table."

#### Scheduled Execution (Cron)

This process should be run once a day to keep the statistics table updated.

#### Programmatic Execution

This process is automatically run every time a user or MSME action adds new data that affects the statistics.
