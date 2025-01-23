FROM mcr.microsoft.com/playwright/python:v1.28.0-focal

# Set up working directory
WORKDIR /app

# Install additional system dependencies
RUN apt-get update && apt-get install -y \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Set display for Playwright
ENV DISPLAY=:99

# Start Xvfb and run the FastAPI application
CMD Xvfb :99 -screen 0 1024x768x16 & uvicorn main:app --host 0.0.0.0 --port 8080
