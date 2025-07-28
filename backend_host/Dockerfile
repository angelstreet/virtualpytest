FROM python:3.11-slim

# Install system dependencies for hardware control and NoVNC
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
    novnc \
    websockify \
    x11vnc \
    fluxbox \
    xterm \
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

# Expose ports
EXPOSE 6109 6080

# Set display environment
ENV DISPLAY=:99

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:6109/host/health || exit 1

# Switch to non-root user
USER vptuser

# Create startup script
RUN echo '#!/bin/bash\n\
set -e\n\
echo "Starting virtual display and desktop services..."\n\
\n\
# Start Xvfb (virtual display)\n\
Xvfb :99 -screen 0 1024x768x24 -ac +extension GLX +render -noreset &\n\
XVFB_PID=$!\n\
\n\
# Wait for Xvfb to start\n\
sleep 2\n\
\n\
# Start window manager\n\
DISPLAY=:99 fluxbox &\n\
FLUXBOX_PID=$!\n\
\n\
# Start x11vnc (VNC server)\n\
x11vnc -display :99 -nopw -listen localhost -xkb -ncache 10 -ncache_cr -forever &\n\
X11VNC_PID=$!\n\
\n\
# Wait for VNC server to start\n\
sleep 2\n\
\n\
# Start NoVNC (web-based VNC client)\n\
websockify --web=/usr/share/novnc/ 6080 localhost:5900 &\n\
NOVNC_PID=$!\n\
\n\
echo "Desktop services started:"\n\
echo "  - Xvfb virtual display on :99"\n\
echo "  - Fluxbox window manager"\n\
echo "  - x11vnc VNC server on :5900"\n\
echo "  - NoVNC web client on :6080"\n\
echo "  - Flask API starting on :6109"\n\
\n\
# Start the main Flask application\n\
exec python src/app.py\n\
' > /home/vptuser/start_services.sh && chmod +x /home/vptuser/start_services.sh

# Run the startup script
CMD ["/home/vptuser/start_services.sh"] 