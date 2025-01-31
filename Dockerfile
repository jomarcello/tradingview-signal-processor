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

# Stel default port in
ENV PORT=8000

# Kopieer en maak het start script uitvoerbaar
COPY start.sh .
RUN chmod +x start.sh

# Start command
CMD ["./start.sh"] 