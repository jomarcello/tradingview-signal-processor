FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
ENV PORT=8000

# Installeer Python en dependencies
RUN apt-get update && apt-get install -y \
    python3.9 \
    python3-pip \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip
RUN python3.9 -m pip install --upgrade pip

# Kopieer en installeer requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Kopieer applicatie bestanden
COPY . .

# Maak start script uitvoerbaar
RUN chmod +x start.sh

# Start via shell om environment variabelen correct te verwerken
CMD ["/bin/bash", "./start.sh"] 