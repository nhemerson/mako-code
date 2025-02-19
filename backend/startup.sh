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

# =============================================
# Cloud Credential Validation
# =============================================
validate_cloud_credentials() {
    # Check if curl is available
    if ! command -v curl &> /dev/null; then
        echo "ERROR: curl is required for credential validation"
        exit 1
    fi

    # Load .env file if present
    if [ -f "$PROJECT_ROOT/.env" ]; then
        source "$PROJECT_ROOT/.env"
    else
        echo "Warning: No .env file found - cloud credentials must be set in environment"
    fi

    # Validate AWS credentials if enabled
    if [ "${AWS_ENABLED:-false}" = "true" ]; then
        if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
            echo "ERROR: AWS enabled but missing AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY"
            exit 1
        fi
        
        echo "Testing AWS credentials..."
        RESPONSE=$(curl -s -f -o /dev/null -w "%{http_code}" \
            "https://sts.amazonaws.com/?Action=GetCallerIdentity&Version=2011-06-15" \
            -H "Authorization: AWS4-HMAC-SHA256 Credential=$AWS_ACCESS_KEY_ID/$(date -u +%Y%m%d)/us-east-1/sts/aws4_request")
        
        if [ "$RESPONSE" != "200" ]; then
            echo "ERROR: AWS credentials validation failed"
            exit 1
        fi
    fi

    # Validate Google Cloud if enabled
    if [ "${GCP_ENABLED:-false}" = "true" ]; then
        if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
            echo "ERROR: GCP enabled but GOOGLE_APPLICATION_CREDENTIALS not set"
            exit 1
        fi
        
        if [ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
            echo "ERROR: GCP service account key file not found at $GOOGLE_APPLICATION_CREDENTIALS"
            exit 1
        fi
        
        echo "Testing GCP credentials..."
        ACCESS_TOKEN=$(curl -s -f -H "Content-Type: application/json" \
            -d "@$GOOGLE_APPLICATION_CREDENTIALS" \
            "https://oauth2.googleapis.com/token" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
        
        if [ -z "$ACCESS_TOKEN" ]; then
            echo "ERROR: Failed to get GCP access token"
            exit 1
        fi

        RESPONSE=$(curl -s -f -o /dev/null -w "%{http_code}" \
            -H "Authorization: Bearer $ACCESS_TOKEN" \
            "https://storage.googleapis.com/storage/v1/b")
        
        if [ "$RESPONSE" != "200" ]; then
            echo "ERROR: GCP credentials validation failed"
            exit 1
        fi
    fi

    # Validate Cloudflare R2 if enabled
    if [ "${R2_ENABLED:-false}" = "true" ]; then
        if [ -z "$R2_ACCOUNT_ID" ] || [ -z "$R2_ACCESS_KEY_ID" ] || [ -z "$R2_SECRET_ACCESS_KEY" ]; then
            echo "ERROR: R2 enabled but missing R2 credentials"
            exit 1
        fi
        
        echo "Testing R2 credentials..."
        TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
        DATE=$(date -u +"%Y%m%d")
        
        ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        RESPONSE=$(curl -s -f -o /dev/null -w "%{http_code}" \
            -H "Host: ${R2_ACCOUNT_ID}.r2.cloudflarestorage.com" \
            -H "X-Amz-Date: $TIMESTAMP" \
            -H "Authorization: AWS4-HMAC-SHA256 Credential=$R2_ACCESS_KEY_ID/$DATE/auto/s3/aws4_request" \
            "$ENDPOINT")
        
        if [ "$RESPONSE" != "200" ]; then
            echo "ERROR: R2 credentials validation failed"
            exit 1
        fi
    fi
}

# Add validation call after config loading
validate_cloud_credentials

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