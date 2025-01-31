#!/bin/bash

# Zorg ervoor dat we een geldige port hebben
if [ -z "$PORT" ]; then
    PORT=8000
fi

# Print debug informatie
echo "Starting server on port: $PORT"
echo "Current directory: $(pwd)"
echo "Files in current directory: $(ls -la)"

# Start Gunicorn met expliciete module:app variabele
exec gunicorn \
    --bind "0.0.0.0:$PORT" \
    --timeout 300 \
    --workers 1 \
    --log-level debug \
    --access-logfile - \
    --error-logfile - \
    "app:app" 