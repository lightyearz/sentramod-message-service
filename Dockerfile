FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies from root context
COPY services/message-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy and install shared library
COPY modai_shared /app/modai_shared
RUN pip install /app/modai_shared

# Copy application code
COPY services/message-service/app /app/app

# Expose port
EXPOSE 8007

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8007/api/v1/health')"

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8007"]
