#!/bin/bash

# Stream logs from containers on EC2 instance
# Usage: ./utils/logs-ec2.sh

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
SSH_KEY="$REPO_ROOT/seatsteal.pem"

# Menu options
options=("notifs" "scraper" "redis" "all (docker-compose logs)")
selected=0

# Function to display menu
display_menu() {
  echo "Select service to view logs:"
  echo "(Use ↑/↓ arrows to navigate, Enter to select)"
  echo ""

  for i in "${!options[@]}"; do
    if [ $i -eq $selected ]; then
      echo "  → ${options[$i]}"
    else
      echo "    ${options[$i]}"
    fi
  done
}

# Clear screen and show menu
clear
echo -e "${YELLOW}📋 EC2 Container Logs${NC}"
echo "================================"
echo ""
display_menu

# Read arrow keys
while true; do
  read -rsn1 key

  if [[ $key == $'\x1b' ]]; then
    read -rsn2 key
    case $key in
      '[A')  # Up arrow
        ((selected--))
        if [ $selected -lt 0 ]; then
          selected=$((${#options[@]} - 1))
        fi
        clear
        echo -e "${YELLOW}📋 EC2 Container Logs${NC}"
        echo "================================"
        echo ""
        display_menu
        ;;
      '[B')  # Down arrow
        ((selected++))
        if [ $selected -ge ${#options[@]} ]; then
          selected=0
        fi
        clear
        echo -e "${YELLOW}📋 EC2 Container Logs${NC}"
        echo "================================"
        echo ""
        display_menu
        ;;
    esac
  elif [[ $key == "" ]]; then
    break
  fi
done

# Set SERVICE and CONTAINER_NAME based on selection
choice=$((selected + 1))

case $choice in
    1)
        SERVICE="notifs"
        CONTAINER_NAME="seatsteal-notifs"
        ;;
    2)
        SERVICE="scraper"
        CONTAINER_NAME="seatsteal-scraper"
        ;;
    3)
        SERVICE="redis"
        CONTAINER_NAME="seatsteal-redis"
        ;;
    4)
        SERVICE="all"
        CONTAINER_NAME=""
        ;;
esac

clear
echo -e "${YELLOW}📋 EC2 Container Logs${NC}"
echo "================================"
echo ""
echo -e "${GREEN}📋 Selected service: $SERVICE${NC}"

# Check if jq is installed for JSON parsing
if ! command -v jq &> /dev/null; then
    echo -e "${RED}❌ Error: jq is not installed (required for JSON parsing).${NC}"
    echo "Please install it: brew install jq (macOS) or apt install jq (Linux)"
    exit 1
fi

# Check if SSH key exists
if [[ ! -f "$SSH_KEY" ]]; then
    echo -e "${RED}❌ Error: SSH key not found at $SSH_KEY${NC}"
    exit 1
fi

# Check SSH key permissions
if [[ "$(stat -f %A "$SSH_KEY")" != "400" ]]; then
    echo -e "${YELLOW}⚠️  Fixing SSH key permissions...${NC}"
    chmod 400 "$SSH_KEY"
fi

# Read EC2 host from JSON file
EC2_HOST_FILE="$SCRIPT_DIR/ec2-host.json"
if [[ ! -f "$EC2_HOST_FILE" ]]; then
    echo -e "${RED}❌ Error: EC2 host file not found at $EC2_HOST_FILE${NC}"
    echo "Run './service.sh → Spin up instance' first."
    exit 1
fi

EC2_HOST=$(jq -r '.public_dns // empty' "$EC2_HOST_FILE" 2>/dev/null || echo "")
if [[ -z "$EC2_HOST" ]]; then
    echo -e "${RED}❌ Error: Could not read public DNS from $EC2_HOST_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}📋 Using EC2 host: $EC2_HOST${NC}"

echo -e "${GREEN}📡 Connecting to ec2-user@$EC2_HOST...${NC}"

# Stream logs from selected container
if [[ "$SERVICE" == "all" ]]; then
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=5 ec2-user@"$EC2_HOST" "cd ~/seatsteal/webapp && docker-compose logs --follow --tail 100"
else
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=5 ec2-user@"$EC2_HOST" "docker logs --follow --tail 100 $CONTAINER_NAME"
fi
