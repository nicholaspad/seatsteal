#!/bin/bash

# SeatSteal Management Script
# Main entry point for deployment and service management

set -e  # Exit on error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Required environment variables for various scripts
# Uses same names as webapp/config.py (source of truth)
REQUIRED_VARS=(
    "VITE_SUPABASE_URL"
    "SUPABASE_SERVICE_ROLE_KEY"
    "AWS_ACCESS_KEY_ID"
    "AWS_SECRET_ACCESS_KEY"
    "AWS_REGION"
    "GITHUB_TOKEN"
)

# Function to load environment variables from .env file if it exists
load_env() {
    local env_file="$SCRIPT_DIR/.env"

    if [[ ! -f "$env_file" ]]; then
        # No .env file - will use current environment variables
        return 1
    fi

    # Read .env file and export variables
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Skip empty lines and comments
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue

        # Extract variable name and value
        if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
            local var_name="${BASH_REMATCH[1]}"
            local var_value="${BASH_REMATCH[2]}"

            # Remove surrounding quotes if present
            var_value="${var_value#\"}"
            var_value="${var_value%\"}"
            var_value="${var_value#\'}"
            var_value="${var_value%\'}"

            # Export the variable
            export "$var_name=$var_value"
        fi
    done < "$env_file"

    return 0
}


# Function to check if all required environment variables are set
check_env_vars() {
    local missing_vars=()

    for var in "${REQUIRED_VARS[@]}"; do
        if [[ -z "${!var}" ]]; then
            missing_vars+=("$var")
        fi
    done

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        return 1
    fi
    return 0
}

# Check environment variables, load from .env if available
if ! check_env_vars; then
    # Try loading from .env file
    if load_env; then
        echo "Loaded environment from .env file"
    else
        echo "No .env file found, using current environment variables"
    fi

    # Check again after loading
    if ! check_env_vars; then
        echo "Error: Missing required environment variables:"
        for var in "${REQUIRED_VARS[@]}"; do
            if [[ -z "${!var}" ]]; then
                echo "  - $var"
            fi
        done
        echo ""
        echo "Please set these variables in your environment or .env file."
        exit 1
    fi
fi

# Function to display menu
display_menu() {
  echo "=========================================="
  echo "  SeatSteal Management"
  echo "=========================================="
  echo ""
  echo "Select an option:"
  echo ""
  echo "  1) EC2"
  echo "  2) Local"
  echo ""
  echo "  0) Exit"
  echo ""
}

# Main loop - allows returning to menu after submenu exits
while true; do
  # Clear screen and show menu
  clear
  display_menu

  # Read user input
  read -r -p "Enter choice: " choice

  case $choice in
    1)
      clear
      ./utils/service.sh
      # After submenu exits, return to main menu
      ;;
    2)
      clear
      ./utils/local.sh
      # After submenu exits, return to main menu
      ;;
    0)
      clear
      echo "Exiting..."
      exit 0
      ;;
    *)
      echo ""
      echo "Invalid option. Please try again."
      sleep 1
      ;;
  esac
done
