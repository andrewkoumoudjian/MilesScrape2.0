#!/bin/bash
# Simple startup script to ensure proper logging and error handling
set -e

echo "Starting MilesScrape 2.0 application..."
echo "Environment: PORT=$PORT"

# Start Gunicorn
exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
