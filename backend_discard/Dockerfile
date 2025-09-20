FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy shared library
COPY shared/ shared/
# Add shared to PYTHONPATH instead of installing as package
ENV PYTHONPATH="/app/shared:/app/shared/src/lib"

# Copy backend_discard requirements and install
COPY backend_discard/requirements.txt backend_discard/
RUN pip install --no-cache-dir -r backend_discard/requirements.txt

# Copy backend_discard source
COPY backend_discard/src/ backend_discard/src/

# Set working directory to backend_discard
WORKDIR /app/backend_discard

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD python -c "from src.app import health_check; exit(0 if health_check() else 1)" || exit 1

# Create non-root user for security
RUN useradd -m -u 1000 discarduser \
    && chown -R discarduser:discarduser /app

USER discarduser

# Run the service
CMD ["python", "src/app.py"]
