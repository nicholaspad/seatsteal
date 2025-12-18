#!/bin/bash

# SeatSteal Management Script
# Main entry point for deployment and service management

set -e  # Exit on error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Required environment variables for various scripts
REQUIRED_VARS=(
    "SUPABASE_URL"
    "SUPABASE_SERVICE_ROLE_KEY"
    "AWS_ACCESS_KEY_ID"
    "AWS_SECRET_ACCESS_KEY"
    "AWS_REGION"
    "GITHUB_TOKEN"
)

# Function to load environment variables from .env file
load_env() {
    local env_file="$SCRIPT_DIR/.env"

    if [[ ! -f "$env_file" ]]; then
        echo "Error: .env file not found at $env_file"
        echo "Please create a .env file with the required environment variables."
        exit 1
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

    # Handle SUPABASE_URL alias (in .env it's VITE_SUPABASE_URL)
    if [[ -z "$SUPABASE_URL" && -n "$VITE_SUPABASE_URL" ]]; then
        export SUPABASE_URL="$VITE_SUPABASE_URL"
    fi

    # Handle AWS_REGION alias (some configs use AWS_DEFAULT_REGION)
    if [[ -z "$AWS_REGION" && -n "$AWS_DEFAULT_REGION" ]]; then
        export AWS_REGION="$AWS_DEFAULT_REGION"
    fi
    if [[ -z "$AWS_DEFAULT_REGION" && -n "$AWS_REGION" ]]; then
        export AWS_DEFAULT_REGION="$AWS_REGION"
    fi
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

# Check environment variables, load from .env if needed
if ! check_env_vars; then
    load_env

    # Check again after loading
    if ! check_env_vars; then
        echo "Error: Missing required environment variables after loading .env:"
        for var in "${REQUIRED_VARS[@]}"; do
            if [[ -z "${!var}" ]]; then
                echo "  - $var"
            fi
        done
        echo ""
        echo "Please ensure these variables are set in your .env file."
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
  echo "  1) Vercel"
  echo "  2) EC2"
  echo "  3) Local"
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
      ./utils/deploy.sh
      # After submenu exits, return to main menu
      ;;
    2)
      clear
      ./utils/service.sh
      # After submenu exits, return to main menu
      ;;
    3)
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
