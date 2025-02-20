#!/bin/bash
# =============================================
# Script Initialization and Path Configuration
# =============================================
# Get the absolute path of the script's directory using BASH_SOURCE
# This works even if the script is sourced or called from another directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get parent directory which is the project root
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# =============================================
# Configuration File Setup
# =============================================
CONFIG_FILE="${MAKO_CONFIG:-$PROJECT_ROOT/config/mako.conf}"
CONFIG_EXAMPLE="$PROJECT_ROOT/config/mako.conf.example"

# If config doesn't exist but example does, create from example
if [ ! -f "$CONFIG_FILE" ] && [ -f "$CONFIG_EXAMPLE" ]; then
    echo "Creating config from example..."
    cp "$CONFIG_EXAMPLE" "$CONFIG_FILE"
fi

# Now try to load the config
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
else
    echo "Error: Configuration file not found at $CONFIG_FILE and could not be created from example."
    exit 1
fi

# =============================================
# Configuration Validation
# =============================================
# Load the validation script that checks config values
# This script validates IP addresses, ports, and environment settings
VALIDATE_SCRIPT="$PROJECT_ROOT/scripts/validate_config.sh"
if [ -f "$VALIDATE_SCRIPT" ]; then
    source "$VALIDATE_SCRIPT"
else
    echo "Error: Validation script not found at $VALIDATE_SCRIPT"
    exit 1
fi

# =============================================
# Default Configuration Setup
# =============================================
# If no config file exists, create one from the example template
# This ensures first-time users have a working configuration
if [ ! -f "../config/mako.conf" ]; then
    echo "Creating config from example..."
    cp ../config/mako.conf.example ../config/mako.conf
fi

# Start Uvicorn server with environment-aware settings
# --------------------------------------------------
# --reload       : Auto-restart on code changes (DEV ONLY - remove in production)
# --host         : Bind address (override with HOST env var or in config)
# --port         : Listener port (override with PORT env var or in config)
# &             : Run in background to allow concurrent processes
.venv/bin/uvicorn main:app --reload --host ${HOST:-0.0.0.0} --port ${PORT:-8000} &

# Suggested configuration file format (config/mako.conf):
# ------------------------------------
# HOST="127.0.0.1"    # For local development
# PORT=3000           # Avoid port conflicts
# LOG_LEVEL="debug"   # Verbose logging
# 
# Production recommendations:
# 1. Remove --reload flag
# 2. Set HOST="0.0.0.0" for external access
# 3. Use reverse proxy (Nginx/Apache) for HTTPS 


# sequenceDiagram
#     User->>mako: ./mako run
#     mako->>startup.sh: Execute
#     startup.sh->>validate_config.sh: Source script
#     validate_config.sh->>Config: Check HOST/PORT
#     validate_config.sh->>Config: Validate ENVIRONMENT
#     validate_config.sh->>Config: Safety checks
#     alt Valid Config
#         startup.sh->>Server: Start normally
#     else Invalid Config
#         startup.sh->>User: Show error
#         startup.sh->>System: Exit with code 1
#     end