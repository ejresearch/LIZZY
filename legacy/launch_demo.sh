#!/bin/bash

# Lizzy Demo Launch Script
# This script launches the Lizzy demo version

echo "=================================================="
echo "  Lizzy Demo - AI Screenplay Writing"
echo "=================================================="
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from example..."
    cp .env.example .env
    echo "Please edit .env file with your API keys before proceeding."
    echo ""
    exit 1
fi

# Check for required Python packages
echo "Checking Python environment..."
python3 -c "import fastapi" 2>/dev/null || {
    echo "Error: FastAPI not found. Please install requirements:"
    echo "  pip install fastapi uvicorn python-dotenv"
    exit 1
}

# Create projects directory if it doesn't exist
mkdir -p projects
mkdir -p logs

echo ""
echo "Starting Lizzy Demo Server..."
echo "Server will be available at: http://localhost:8003"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Launch the server
cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python3 servers/landing_server.py
