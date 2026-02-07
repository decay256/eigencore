# =============================================================================
# Eigencore API Dockerfile
# =============================================================================
# This is a multi-stage build that creates a small, efficient production image.
# 
# Multi-stage means we use one image to BUILD (with all dev tools),
# then copy only what we need into a SLIM image for running.
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder
# -----------------------------------------------------------------------------
# We use the full Python image here because we need pip and build tools
# to install dependencies (some packages need to compile C extensions).

FROM python:3.12-slim as builder

# Set working directory inside the container
WORKDIR /app

# Install system dependencies needed to build Python packages
# - gcc: C compiler for packages with C extensions
# - libpq-dev: PostgreSQL client library (needed for asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (Docker layer caching optimization)
# If requirements.txt hasn't changed, Docker reuses the cached layer
# and doesn't reinstall all packages — saves time on rebuilds!
COPY requirements.txt .

# Install Python dependencies into a virtual environment
# --no-cache-dir: Don't store pip's cache (smaller image)
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt


# -----------------------------------------------------------------------------
# Stage 2: Production image
# -----------------------------------------------------------------------------
# Now we create the actual image that will run. It's much smaller because
# it doesn't include build tools — only the runtime.

FROM python:3.12-slim as production

# Labels for container registry (optional but good practice)
LABEL org.opencontainers.image.title="Eigencore API"
LABEL org.opencontainers.image.description="Game backend API for indie games"

# Create a non-root user for security
# Running as root inside containers is a security risk
RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Install runtime dependencies only (no build tools)
# libpq5: PostgreSQL client library (runtime version, not -dev)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from builder stage
# This is the magic of multi-stage builds — we only copy what we need
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
# We do this late so code changes don't invalidate the dependency cache
COPY --chown=appuser:appgroup . .

# Switch to non-root user
USER appuser

# Expose the port uvicorn will listen on
# This is documentation — you still need to publish it with -p when running
EXPOSE 8000

# Health check — Docker/orchestrators use this to know if the container is healthy
# It hits our /health endpoint every 30 seconds
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default command to run the application
# - --host 0.0.0.0: Listen on all interfaces (required in containers)
# - --port 8000: The port we exposed above
# - --workers 1: Single worker (increase for production, or use Gunicorn)
#
# For production with multiple workers, consider:
# CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
