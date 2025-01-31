#!/bin/bash
set -x

# Installeer Playwright browsers
python -m playwright install chromium
export PLAYWRIGHT_BROWSERS_PATH=0

# Zorg voor juiste rechten
chmod -R 777 /home/railway/.cache/ms-playwright 