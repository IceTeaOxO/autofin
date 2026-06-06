FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for build
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and config
COPY src/ ./src/
COPY config.yaml .
COPY README.md .

# Create data and logs directories
RUN mkdir -p data logs

# Environment variables (Defaults)
ENV EMAIL_API_URL="http://100.124.61.26/mail-sender/api/v1/email/send"
ENV EMAIL_RECIPIENT="uchuang9128@gmail.com"
ENV PYTHONPATH="/app/src"

# Run command (Data fetch -> Factor calc -> Strategy with notify)
CMD ["sh", "-c", "python3 src/main_data.py && python3 src/main_factors.py && python3 src/main_strategy.py --notify"]
