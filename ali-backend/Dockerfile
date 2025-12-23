# Use official lightweight Python image
FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements first (to cache dependencies)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Set environment variable for Cloud Run
ENV PORT=8080

# Run the app using Gunicorn (Production Server)
# We bind to 0.0.0.0 so Cloud Run can reach it
CMD exec uvicorn app.main:app --host 0.0.0.0 --port $PORT