FROM python:3.11

RUN groupadd -r runner && useradd --no-log-init -r -g runner runner

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /workdir
USER runner:runner
COPY --chown=runner:runner . .

ENV WEB_CONCURRENCY=2

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]
