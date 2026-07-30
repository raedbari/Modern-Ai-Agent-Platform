#!/bin/bash
# Setup script for testing

echo "Installing dependencies..."
pip install -q -r requirements.txt

echo "Running tests..."
python -m pytest tests/ -v --tb=short

echo "Test run complete!"
