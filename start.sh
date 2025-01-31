#!/bin/bash
PORT="${PORT:-8000}"
exec gunicorn --bind "0.0.0.0:$PORT" --timeout 300 --workers 1 app:app 