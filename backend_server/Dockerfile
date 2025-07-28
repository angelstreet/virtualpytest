FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-0 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy shared library
COPY shared/ shared/
# Add shared to PYTHONPATH instead of installing as package
ENV PYTHONPATH="/app/shared:/app/shared/lib:/app/backend_core/src"

# Copy backend_core (required dependency)
COPY backend_core/ backend_core/

# Copy backend_server requirements and install
COPY backend_server/requirements.txt backend_server/
RUN pip install --no-cache-dir -r backend_server/requirements.txt

# Copy backend_server source
COPY backend_server/src/ backend_server/src/

# Copy utils directory (if it exists in project root)
# Note: This copy is optional and will be skipped if src/utils/ doesn't exist

# Set working directory to backend_server
WORKDIR /app/backend_server

# Create non-root user for security
RUN useradd -m -u 1000 vptuser && chown -R vptuser:vptuser /app

# Expose port
EXPOSE 5109

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:5109/server/health || exit 1

# Switch to non-root user
USER vptuser

# Run the application
CMD ["python", "src/app.py"] 