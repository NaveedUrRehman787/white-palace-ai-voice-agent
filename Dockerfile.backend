# ============================================
# White Palace Grill - Flask Backend
# Production-ready Dockerfile
# ============================================

FROM python:3.12-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_ENV=production

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create app directory
WORKDIR /app

# Copy unified requirements from root
COPY requirements.txt ./

# Install Python dependencies
# We use a recent version of eventlet known to work with Python 3.12
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install eventlet>=0.35.2

# Copy the backend directory
COPY backend/ ./backend/

# Set working directory to the backend folder
WORKDIR /app/backend

# Ensure the backend directory is in the python path
ENV PYTHONPATH=/app/backend:/app

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 5000

# Health check - give it more time to boot
HEALTHCHECK --interval=30s --timeout=15s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Run with gunicorn for production
# Workers set to 1 for SocketIO stability
# We use 'app:app' because we are inside the /app/backend directory
CMD ["gunicorn", \
    "--worker-class", "eventlet", \
    "--workers", "1", \
    "--bind", "0.0.0.0:5000", \
    "--timeout", "120", \
    "--access-logfile", "-", \
    "--error-logfile", "-", \
    "app:app"]
