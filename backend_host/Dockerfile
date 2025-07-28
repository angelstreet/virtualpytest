FROM python:3.11-slim

# Install system dependencies for hardware control
RUN apt-get update && apt-get install -y \
    xvfb \
    x11-utils \
    scrot \
    python3-tk \
    python3-dev \
    libopencv-dev \
    ffmpeg \
    curl \
    wget \
    gcc \
    g++ \
    make \
    build-essential \
    linux-libc-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy shared library and backend_core
COPY shared/ shared/
COPY backend_core/ backend_core/

# Add shared and backend_core to PYTHONPATH instead of installing as packages
ENV PYTHONPATH="/app/shared:/app/shared/lib:/app/backend_core/src"

# Copy backend_host requirements and install
COPY backend_host/requirements.txt backend_host/
RUN pip install --no-cache-dir -r backend_host/requirements.txt

# Copy backend_host source
COPY backend_host/src/ backend_host/src/

# Copy utils directory (if it exists in project root)
# Note: This copy is optional and will be skipped if src/utils/ doesn't exist

# Set working directory to backend_host
WORKDIR /app/backend_host

# Create non-root user for security
RUN useradd -m -u 1000 vptuser && chown -R vptuser:vptuser /app

# Expose port
EXPOSE 6109

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:6109/host/health || exit 1

# Switch to non-root user
USER vptuser

# Run the application
CMD ["python", "src/app.py"] 