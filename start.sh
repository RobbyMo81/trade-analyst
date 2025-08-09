#!/bin/bash
# Unix/Linux shell script to start Trade Analyst application

echo "Starting Trade Analyst Application..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "Error: Failed to activate virtual environment"
    exit 1
fi

# Install dependencies if requirements.txt is newer than last install
if [ ! -f ".last_install" ] || [ "requirements.txt" -nt ".last_install" ]; then
    echo "Installing/updating dependencies..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install dependencies"
        exit 1
    fi
    touch .last_install
fi

# Start the application
echo ""
echo "Starting Trade Analyst..."
echo "Press Ctrl+C to stop the application"
echo ""

python start.py server "$@"

# Deactivate virtual environment
deactivate

echo ""
echo "Trade Analyst stopped."
