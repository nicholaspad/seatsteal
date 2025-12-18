FROM python:3.11-slim

# Install system dependencies and CLI tools
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    git \
    curl \
    unzip \
    ca-certificates \
    gnupg \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js and npm (for Vercel CLI)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Vercel CLI globally
RUN npm install -g vercel

# Install AWS CLI
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -rf aws awscliv2.zip

WORKDIR /app

# Copy requirements first for better caching
COPY terminal-server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY terminal-server/app.py .

# Copy management scripts and utilities from repository root
COPY manage.sh .
COPY utils/ ./utils/
RUN chmod +x manage.sh

# Set terminal environment variable
ENV TERM=xterm-256color

# Create non-root user for security
RUN useradd -m -s /bin/bash appuser

# Copy scripts must be readable by appuser
RUN chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 10000

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000"]
