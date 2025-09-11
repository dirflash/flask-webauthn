FROM python:3.10-slim-bullseye

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    wait-for-it \
    build-essential \
    python3-dev \
    curl \
    postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py

# Create app directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org -r requirements.txt

# Copy application code
COPY . /app

# Make entrypoint script executable
RUN chmod +x ./entrypoint.sh

# Expose port
EXPOSE 5000

# Run the application
CMD ["./entrypoint.sh"]