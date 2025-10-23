#!/bin/bash

set -e

VENV_DIR=".venv"
REQUIREMENTS_FILE="requirements.txt"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment: $VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

echo "Activating virtual environment"
source "$VENV_DIR/bin/activate"

if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "Installing Python dependencies from $REQUIREMENTS_FILE"
    pip install -r "$REQUIREMENTS_FILE"
else
    echo "No $REQUIREMENTS_FILE found. Skipping dependency installation."
fi
