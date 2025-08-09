# Multi-stage Docker build for Trade Analyst Application

# Build stage
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_ENVIRONMENT=production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r tradeuser && useradd -r -g tradeuser tradeuser

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=tradeuser:tradeuser . .

# Create necessary directories
RUN mkdir -p data logs tokens && \
    chown -R tradeuser:tradeuser /app

# Switch to non-root user
USER tradeuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command
CMD ["python", "start.py", "server", "--host", "0.0.0.0", "--port", "8080"]

# Labels
LABEL maintainer="Trade Analyst Team" \
      version="1.0.0" \
      description="Trade Analyst Application for financial data processing" \
      org.opencontainers.image.source="https://github.com/your-org/trade-analyst" \
      org.opencontainers.image.title="Trade Analyst" \
      org.opencontainers.image.description="Financial data analysis and processing application" \
      org.opencontainers.image.version="1.0.0"
