#!/bin/bash

# Start Lizzy 2.0 Landing Page Server

echo "=================================="
echo "Lizzy 2.0 Landing Page"
echo "=================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "ERROR: Virtual environment not found!"
    echo "Please create one first: python3 -m venv venv"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if dependencies are installed
python3 -c "import fastapi, uvicorn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing dependencies..."
    pip install fastapi uvicorn
fi

# Start server
echo "Starting landing page server..."
echo ""
echo "   Landing page: http://localhost:8002"
echo "   API docs: http://localhost:8002/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Set PYTHONPATH to include project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Run from project root
cd "$(dirname "$0")/.." && python3 servers/landing_server.py
