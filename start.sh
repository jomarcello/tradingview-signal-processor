#!/bin/bash

# Zorg ervoor dat we een geldige port hebben
if [ -z "$PORT" ]; then
    PORT=8000
fi

# Print debug informatie
echo "Starting server on port: $PORT"

# Start Gunicorn
exec gunicorn --bind "0.0.0.0:$PORT" \
    --timeout 300 \
    --workers 1 \
    --log-level debug \
    app:app 