#!/bin/bash

# Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate the virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Uninstall existing packages to avoid conflicts
pip uninstall -y openai httpx

# Install dependencies with specific versions
pip install -r requirements.txt

echo "Setup complete! You can now run the program with:"
echo "source venv/bin/activate"
echo "python rag_challenge.py" 