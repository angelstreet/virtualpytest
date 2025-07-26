FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy shared library
COPY shared/ shared/
RUN pip install --no-cache-dir -e shared/

# Copy backend-server requirements and install
COPY backend-server/requirements.txt backend-server/
RUN pip install --no-cache-dir -r backend-server/requirements.txt

# Copy backend-server source
COPY backend-server/src/ backend-server/src/

# Copy utils directory (if it exists in project root)
COPY src/utils/ backend-server/src/utils/ 2>/dev/null || echo "No utils directory found"

# Set working directory to backend-server
WORKDIR /app/backend-server

# Create non-root user for security
RUN useradd -m -u 1000 vptuser && chown -R vptuser:vptuser /app

# Expose port
EXPOSE 5109

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:5109/api/health || exit 1

# Switch to non-root user
USER vptuser

# Run the application
CMD ["python", "src/app.py"] 