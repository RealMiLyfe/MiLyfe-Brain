FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    gcc \
    g++ \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install --with-deps chromium

# Application code
COPY . .

# Create workspace and data directories
RUN mkdir -p /workspace /data

# Expose port
EXPOSE 8200

# Health check
HEALTHCHECK --interval=15s --timeout=10s --retries=5 \
    CMD curl -f http://localhost:8200/health || exit 1

# Run with single worker (required for shared state)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8200", "--workers", "1", "--log-level", "info"]
