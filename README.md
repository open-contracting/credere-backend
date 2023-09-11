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
- SENTRY_DSN -> the DSN for sentry
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
- TEST_DATABASE_URL -> Local test database in order to not drop and generate the main local database all the time
- PROGRESS_TO_REMIND_STARTED_APPLICATIONS -> % of days of lender SLA before an overdue reminder, for example a lender with a SLA of 10 days will receive the first overdue at 7 days mark
- ENVIRONMENT -> needs to be set as "production" in order to send emails to real borrower address. If not, emails will be sent to TEST_MAIL_RECEIVER

You should configure the pre-commit for the repo one time

```
pre-commit install
```

## Repository structure

```
app/                                      # Main application module
│ ├── main.py                             # Main FastAPI application entry point
│ ├── init.py                             # Initialization of the application
│ ├── commands.py                         # Contains Typer commands to run background processes
│ ├── routers/                            # FastAPI routers for dividing the app into smaller sub-applications
│ │ ├── applications.py                   # Router for application endpoints
│ │ ├── statistics.py                     # Router for statistics endpoints
│ │ ├── awards.py                         # Router for awards endpoints
│ │ ├── users.py                          # Router for user endpoints
│ │ ├── security.py                       # Router for security related endpoints
│ │ ├── borrowers.py                      # Router for borrower endpoints
│ │ └── lenders.py                        # Router for lender endpoints
│ ├── utils/                              # Contains utility functions for the application
│ │ ├── permissions.py                    # Utility for managing permissions
│ │ ├── verify_token.py                   # Utility for JWT token verification
│ │ ├── general_utils.py                  # General utility functions for the app
│ │ ├── applications.py                   # Utility functions specific to applications
│ │ ├── email_utility.py                  # Utility for email handling
│ │ ├── users.py                          # Utility functions specific to users
│ │ └── lenders.py                        # Utility functions specific to lenders
│ ├── db/                                 # Handles SQLAlchemy database operations
│ │ ├── session.py                        # SQLAlchemy session management
│ ├── core/                               # Contains core settings and configurations
│ │ ├── email_templates.py                # Email templates for the application
│ │ ├── settings.py                       # Main settings file for the application, might contain FastAPI and database configurations
│ │ └── user_dependencies.py              # Manages user dependencies, possibly through FastAPI's dependency injection
│ ├── background_processes/               # Background tasks for the application
│ │ ├── application_utils.py              # Utility functions related to applications
│ │ ├── lapsed_applications.py            # Set applications as lapsed, if the conditions are met, available as a command
│ │ ├── update_statistic.py               # Updates statistics, available as a command
│ │ ├── colombia_data_access.py           # Handles data retrieval and processing for contracts, awards, and borrowers.
│ │ ├── remove_data.py                    # Handles removal of dated application data, available as a command
│ │ ├── awards_utils.py                   # Utility functions related to awards
│ │ ├── fetcher.py                        # Fetches new awards, available as a command
│ │ ├── send_reminder.py                  # Sends reminders mails, available as a command
│ │ ├── SLA_overdue_applications.py       # Sets overdue applications, available as a command
│ │ ├── background_utils.py               # General utilities
│ │ ├── statistics_utils.py               # Utility functions for statistics
│ │ ├── message_utils.py                  # Utility functions for messaging
│ │ └── borrower_utils.py                 # Utility functions for borrowers
│ ├── email_templates/                    # Contains email templates for the application
│ └── schema/                             # Contains SQLAlchemy schema definitions for the application
│ ├── diagram                             # Diagram for the schema
│ ├── statistic.py                        # Statistic schema definition
│ ├── core.py                             # Core schema definition
│ ├── api.py                              # API schema definition
│ └── user_tables/                        # User table schema definition



```

## Development process

### Indentation and formatting

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

You can get coverage information in console by running the following command

```
pytest --cov
```

and you can generate an html report using the following command

```
pytest --cov --cov-report=html:coverage_re
```

this will creat a folder called coverage_re in your project

## Documentation

To run sphinx server

first install sphinx and autobuild

```
pip install furo sphinx-autobuild
```

```
sphinx-autobuild -q docs docs/_build/html --watch .
```

## Background jobs Commands

To run the list of commands available use

```
python -m app.commands --help
```

The background processes are set to run as cron jobs in the server.
You can configure this using

```
crontab -e
```

### Ccommand to fetch new awards is

```
python -m app.commands fetch-awards
```

or

```
python -m app.commands fetch-awards --email-invitation test@example.com
```

These commands gets new contracts since the last updated award date. For each new contract, an award is created, a borrower is either retrieved or created, and if the borrower has not declined opportunities, an application is created for them. An invitation email is sent to the borrower (or the test email, depending on env variables _ENVIRONMENT_ and _TEST_MAIL_RECEIVER_ values).

Alternative could receive a custom email destination with **--email-invitation** argument

#### Scheduled Execution (Cron)

This process should be run once a day. In the cron editor, and considere the deployment using th docker-compose of the project, you can use

```
0 4 * * * /usr/bin/docker exec credere-backend-1 python -m app.commands fetch-awards >> /dev/null 2>&1
```

### Command to remove user data from dated applications

```
python -m app.commands remove-dated-application-data
```

Queries the applications in 'declined', 'rejected', 'completed', and 'lapsed' status that have remained in these states longer than the time defined in the environment variable _DAYS_TO_ERASE_BORROWERS_DATA_. If no other application is using the data, it deletes all the personal data of the borrower (name, email, address, legal identifier)."

#### Scheduled Execution (Cron)

This process should be run once a day.

```
0 5 * * * /usr/bin/docker exec credere-backend-1 python -m app.commands remove-dated-application-data >> /dev/null 2>&1
```

### Command to set application status to lapsed

```
python -m app.commands update-applications-to-lapsed

```

Queries the applications in 'PENDING', 'ACCEPTED', and 'INFORMATION*REQUESTED' status that have remained in these states longer than the time defined in the environment variable \_DAYS_TO_CHANGE_TO_LAPSED*, and changes their status to 'LAPSED'.

#### Scheduled Execution (Cron)

This process should be run once a day to keep the application's status updated.

```
0 6 * * * /usr/bin/docker exec credere-backend-1 python -m app.commands update-applications-to-lapsed >> /dev/null 2>&1
```

### Command to send mail reminders is

```
python -m app.commands send-reminders
```

- Queries the applications in 'PENDING' status that fall within the range leading up to the expiration date. This range is defined by the environment variable _REMINDER_DAYS_BEFORE_EXPIRATION_.

- The intro reminder email is sent to the applications that fulfill the previous condition.

- Queries the applications in 'ACCEPTED' status that fall within the range leading up to the expiration date. This range is defined by the environment variable _REMINDER_DAYS_BEFORE_EXPIRATION_.

- The submit reminder email is sent to the applications that fulfill the previous condition.

#### Scheduled Execution (Cron)

This process should be run once a day.

```
0 7 * * * /usr/bin/docker exec credere-backend-1 python -m app.commands send-reminders >> /dev/null 2>&1
```

### Command to send overdue appliations emails to FI users is

```
python -m app.commands sla-overdue-applications
```

This command identifies applications that are in 'INFORMATION_REQUESTED' or 'STARTED' status and overdue based on the lender's service level agreement (SLA). For each overdue application, an email is sent to OCP and to the respective lender. The command also updates the **overdued_at** attribute for applications that exceed the lender's SLA days.

#### Scheduled Execution (Cron)

This process should be run once a day to ensure that all necessary parties are notified of overdue applications in a timely manner.

```
0 8 * * * /usr/bin/docker exec credere-backend-1 python -m app.commands sla-overdue-applications >> /dev/null 2>&1
```

### Command to update statistics is

```
python -m app.commands update-statistics
```

Performs the calculation needed to populate the statistic table with data from other tables, mainly, the Applications table.

#### Scheduled Execution (Cron)

This process should be run once a day to keep the statistics table updated.

```
0 6 * * * /usr/bin/docker exec credere-backend-1 python -m app.commands update-statistics >> /dev/null 2>&1
```

#### Statistics updates

This process is automatically run every time a user or MSME action adds new data that affects the statistics.
The enpoints that update statistics are:

- post "/applications/access-scheme"
- post "/applications/{id}/reject-application",
- post "/applications/{id}/complete-application",
- post "/applications/{id}/approve-application",
- post "/applications/{id}/start"
- post "/applications/confirm-credit-product",
- post "/applications/submit"
- post "/applications/email-sme/"
- post "/applications/complete-information-request"
- post "/applications/decline"
- post "/applications/rollback-decline",
- post "/applications/decline-feedback"

## First admin user set up

1. Create a user in Cognito
- Create the user manually in the pool from the AWS console.
- Mark "Don’t send invitation" and mark the option of verified email address.
- After adding the new user to the pool, get the username from Cognito.

2. Create the user in the Credere database
- Insert in the user table from the Credere database a record for the user.
- INSERT INTO public.credere_user(type, language, email, name, external_id)
VALUES ("OCP", "es", {EMAIL}, “Admin User”, {COGNITO_USER_ID});

3. Reset the password through the Frontend
- Go to the login page
- Click "Forgot Password?"
- You will receive the email to set the password and after that configure the MFA for the new user.
