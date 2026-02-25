FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables to prevent crashes
ENV PYTHONUNBUFFERED=1
ENV CHROMA_TELEMETRY_OFF=True
ENV ANONYMIZED_TELEMETRY=False
ENV TOKENIZERS_PARALLELISM=false

RUN pip install --no-cache-dir --upgrade pip "setuptools<81"

COPY requirements.txt .
ARG CACHEBUST=1
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Use single worker to avoid multiprocessing issues with tiktoken
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--loop", "asyncio"]
