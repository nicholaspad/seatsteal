FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements-full.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-full.txt

# Copy application code
COPY . .

# Set Python path
ENV PYTHONPATH=/app

# Run Celery worker and Beat together
# Worker processes notification tasks, Beat schedules them
CMD celery -A notifications.daemon.tasks:celery_app worker --beat --loglevel=info --concurrency=2
