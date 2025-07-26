FROM python:3.11-slim

WORKDIR /app/shared

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared library code
COPY lib/ lib/
COPY setup.py .

# Install shared library
RUN pip install -e .

# Create volume for sharing
VOLUME ["/app/shared"]

CMD ["tail", "-f", "/dev/null"] 