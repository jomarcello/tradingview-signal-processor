FROM python:3.11-slim
WORKDIR /app

# Installeer alleen benodigde dependencies
RUN pip install flask requests python-dotenv

# Kopieer alleen relevante bestanden
COPY ai_signal_processor.py .
COPY .env.production ./.env  # Gebruik .env.production als bron

CMD ["python", "ai_signal_processor.py"] 