FROM python:3.11

RUN \
 apk add --no-cache python3 postgresql-libs && \
 apk add --no-cache --virtual .build-deps gcc python3-dev musl-dev postgresql-dev libffi-dev openssl-dev && \
 pip install --ignore-installed uvicorn==0.22.0 \
 apk --purge del .build-deps

RUN groupadd -r runner && useradd --no-log-init -r -g runner runner

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /workdir
USER runner:runner

COPY --chown=runner:runner . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
