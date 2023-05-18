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

### Poetry

To ease development around virtualenv and dependencies, [Poetry](https://python-poetry.org/docs/) is configured. You can [install Poetry](https://python-poetry.org/docs/#installation) and the install the dependencies in the virtualenv managed by Poetry

```
poetry install
```

You should configure the pre-commit for the repo one time

```
poetry run pre-commit install
```

To activate the virtualenv with run, this is needed to run the commands installed as dependencies, such as pre-commit or pytest.

```
poetry shell
```

Run the uvicorn server in the virtualenv, use

```
uvicorn app.main:app --reload
```

### Without Poetry

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

## Test

To run test locally

```
pytest tests -W error
```
