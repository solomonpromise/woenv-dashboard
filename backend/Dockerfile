FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Checked out from Windows the file arrives without an executable bit.
RUN chmod +x start.sh

# Informational only - Render overrides this with its own $PORT.
EXPOSE 8000

# start.sh migrates the schema, then execs uvicorn. --reload is deliberately
# absent: the source is baked into the image, so it watched files that could
# never change while doubling the process count on a 512 MB instance.
CMD ["./start.sh"]
