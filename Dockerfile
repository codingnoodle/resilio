# 🏆 Bonus Point: Deployment Configuration
# Optimized for Google Cloud Run
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies (curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src
COPY ui/ ./ui

# Set environment variables for Streamlit
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Expose Streamlit port (Cloud Run uses PORT env var, but we set it explicitly)
EXPOSE 8080

# Health check for container orchestration
# Streamlit health endpoints: /healthz (if enabled) or /_stcore/health
# Fallback to root endpoint if health endpoints are not available
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f -s http://localhost:8080/healthz >/dev/null 2>&1 || \
        curl -f -s http://localhost:8080/_stcore/health >/dev/null 2>&1 || \
        curl -f -s http://localhost:8080/ >/dev/null 2>&1 || \
        exit 1

# Run the Control Tower
CMD ["streamlit", "run", "ui/dashboard.py", "--server.port=8080", "--server.address=0.0.0.0"]