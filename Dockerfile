FROM python:3.11.3-alpine3.18

# 
WORKDIR /code

#

COPY ./requirements.txt /code/requirements.txt
RUN \
 apk add --no-cache python3 postgresql-libs && \
 apk add --no-cache --virtual .build-deps gcc python3-dev musl-dev postgresql-dev libffi-dev openssl-dev && \
 pip install --ignore-installed uvicorn==0.22.0 && \
 pip install --no-cache-dir --upgrade -r /code/requirements.txt && \
 apk --purge del .build-deps

# 
COPY ./app /code/app
COPY ./.env /code/.env
COPY ./migrations /code/migrations
COPY ./alembic.ini /code/alembic.ini
# 
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]