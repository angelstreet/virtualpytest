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
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy shared library and backend-core
COPY shared/ shared/
COPY backend-core/ backend-core/

# Install shared dependencies
RUN pip install --no-cache-dir -e shared/
RUN pip install --no-cache-dir -e backend-core/

# Copy backend-host requirements and install
COPY backend-host/requirements.txt backend-host/
RUN pip install --no-cache-dir -r backend-host/requirements.txt

# Copy backend-host source
COPY backend-host/src/ backend-host/src/

# Copy utils directory (if it exists in project root)
COPY src/utils/ backend-host/src/utils/ 2>/dev/null || echo "No utils directory found"

# Set working directory to backend-host
WORKDIR /app/backend-host

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