#!/bin/bash

# Function to validate IP address format
validate_ip() {
    local ip=$1
    if [[ ! $ip =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] && [[ $ip != "localhost" ]]; then
        echo "Invalid IP address format: $ip"
        exit 1
    fi
    
    # Check each octet for valid range (0-255)
    if [[ $ip =~ ^[0-9] ]]; then  # Only check if not localhost
        IFS='.' read -r -a octets <<< "$ip"
        for octet in "${octets[@]}"; do
            if [[ $octet -lt 0 ]] || [[ $octet -gt 255 ]]; then
                echo "Invalid IP address range: $ip"
                exit 1
            fi
        done
    fi
}

# Check required config values
: "${HOST:?HOST must be set}"
: "${PORT:?PORT must be set}"
: "${ENVIRONMENT:?ENVIRONMENT must be set}"

# Validate HOST format
validate_ip "${HOST}"

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(development|production)$ ]]; then
    echo "Invalid ENVIRONMENT: $ENVIRONMENT"
    exit 1
fi

# Ensure production safety
if [ "$ENVIRONMENT" == "production" ] && [ "$DEV_RELOAD" == "true" ]; then
    echo "WARNING: Auto-reload enabled in production!"
    sleep 5  # Give chance to cancel
fi