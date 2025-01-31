FROM python:3.9-slim

WORKDIR /app

# Installeer systeemafhankelijkheden
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Kopieer requirements
COPY requirements.txt .

# Installeer Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Kopieer de applicatiecode
COPY . .

# Verhoog de memory limit
ENV MALLOC_ARENA_MAX=2

# Stel default port in voor het geval $PORT niet beschikbaar is
ENV PORT=8000

# Start command met PORT environment variable
CMD gunicorn --bind 0.0.0.0:${PORT} --timeout 300 --workers 1 app:app 