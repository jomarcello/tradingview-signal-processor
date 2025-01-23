FROM mcr.microsoft.com/playwright/python:v1.28.0-focal

# Install system dependencies
RUN apt-get update && apt-get install -y \
    xvfb \
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
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libwayland-client0 \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser
RUN playwright install chromium

# Copy the application code
COPY . .

# Set display for Playwright
ENV DISPLAY=:99

# Start Xvfb and run the FastAPI application
CMD Xvfb :99 -screen 0 1024x768x16 & uvicorn main:app --host 0.0.0.0 --port 8080
