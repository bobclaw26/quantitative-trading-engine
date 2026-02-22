#!/bin/bash

# Trading Engine - Local Implementation
# This script runs the entire trading engine with cron scheduling

WORKSPACE_DIR="/home/bob/.openclaw/workspace/trading-engine"
VENV_DIR="$WORKSPACE_DIR/venv"
ENGINE_DIR="$WORKSPACE_DIR/engine"
LOG_DIR="$WORKSPACE_DIR/logs"

# Ensure logs directory exists
mkdir -p $LOG_DIR

# Activate virtual environment
source $VENV_DIR/bin/activate

# Run the main script
cd $ENGINE_DIR
exec python3 main.py "$@"
