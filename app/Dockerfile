FROM python:3.10-slim-bullseye

RUN apt-get update && \
	apt-get install -y --no-install-recommends ca-certificates wait-for-it build-essential python3-dev curl && \
	rm -rf /var/lib/apt/lists/*
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org -r requirements.txt
COPY . /app

CMD sh ./entrypoint.sh