FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Copy management scripts and utilities
COPY manage.sh .
COPY utils/ ./utils/
RUN chmod +x manage.sh

# Create non-root user for security
RUN useradd -m -s /bin/bash appuser
USER appuser

# Expose port
EXPOSE 10000

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000"]
