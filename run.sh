#!/bin/bash

# Run script for MilesScrape 2.0

# Check for virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt

# Run the Flask app
echo "Starting MilesScrape 2.0 application..."
export FLASK_APP=app.py
export FLASK_ENV=development
flask run --host=0.0.0.0