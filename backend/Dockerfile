FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create dedicated data directory for SQLite database persistence & synthetic dataset
RUN mkdir -p /app/data /data

# Copy application source code
COPY app/ ./app/

# Expose backend API port
EXPOSE 8000

# Set environment defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production \
    DEBUG=false \
    DATABASE_URL=sqlite:///./data/revora.db

# Launch FastAPI via Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
