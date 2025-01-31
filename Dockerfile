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

# Expose de port die uw applicatie gebruikt
EXPOSE 8000

# Start command
CMD ["python", "app.py"] 