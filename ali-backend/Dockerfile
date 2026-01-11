# Use official lightweight Python image
FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements first (to cache dependencies)
COPY requirements.txt .

# Install dependencies
# Install system dependencies for Playwright and FFmpeg
# Note: fonts-ubuntu and fonts-unifont are the new package names in Debian Trixie
# (previously ttf-ubuntu-font-family and ttf-unifont)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    fonts-liberation \
    fonts-unifont \
    fonts-noto-color-emoji \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Install Common Python Dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Browsers (Chromium only, skip system deps since we installed them above)
RUN playwright install chromium

# Copy the rest of the app
COPY . .

# Set environment variable for Cloud Run
ENV PORT=8080

# Run the app using Gunicorn (Production Server)
# We bind to 0.0.0.0 so Cloud Run can reach it
CMD exec uvicorn app.main:app --host 0.0.0.0 --port $PORT