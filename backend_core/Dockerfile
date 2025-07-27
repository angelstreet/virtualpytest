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
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy shared library first
COPY shared/ shared/
RUN pip install --no-cache-dir -e shared/

# Copy backend_core requirements and install
COPY backend_core/requirements.txt backend_core/
RUN pip install --no-cache-dir -r backend_core/requirements.txt

# Copy backend_core source
COPY backend_core/src/ backend_core/src/
COPY backend_core/setup.py backend_core/

# Install backend_core
RUN pip install -e backend_core/

# Set working directory to backend_core
WORKDIR /app/backend_core

# Create non-root user for security
RUN useradd -m -u 1000 vptuser && chown -R vptuser:vptuser /app
USER vptuser

# Expose port (not used in core, but for consistency)
EXPOSE 8000

CMD ["python", "-c", "import backend_core; print('Backend Core Ready')"] 