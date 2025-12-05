# ------------------------------
# Stage 1: Build / install dependencies
# ------------------------------
FROM python:3.12-slim AS builder

WORKDIR /app

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install into dedicated folder
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ------------------------------
# Stage 2: Final minimal image
# ------------------------------
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy the script
COPY docker_dashboard.py .

# Optional: copy .env if you want defaults inside image
COPY .env ./

# Install runtime-only dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    sshpass \
    && rm -rf /var/lib/apt/lists/*

# Set default command
CMD ["python", "docker_dashboard.py"]
