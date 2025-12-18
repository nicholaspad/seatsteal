#!/bin/bash

# Kill containers on EC2 instance
# Usage: ./utils/kill-containers-ec2.sh

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

echo -e "${YELLOW}🛑 EC2 Container Killer${NC}"
echo "================================"
echo ""

# Sync credentials from Supabase if local files don't exist (for terminal-server redeployments)
source "$SCRIPT_DIR/ec2-credentials.sh"
sync_credentials || true

# Function to display menu
display_menu() {
  echo "Select service to kill:"
  echo ""
  echo "  1) notifs"
  echo "  2) scraper"
  echo "  3) all (notifs + scraper)"
  echo ""
  echo "  0) Cancel"
  echo ""
}

# Show menu
display_menu

# Read user input
read -r -p "Enter choice: " choice

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
        SERVICE="all"
        CONTAINER_NAME=""
        ;;
    0)
        echo "Cancelled."
        exit 0
        ;;
    *)
        echo "Invalid option."
        exit 1
        ;;
esac

clear
echo -e "${YELLOW}🛑 EC2 Container Killer${NC}"
echo "================================"
echo ""
echo -e "${GREEN}🎯 Selected service: $SERVICE${NC}"

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

# Kill selected container(s)
if [[ "$SERVICE" == "all" ]]; then
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=5 ec2-user@"$EC2_HOST" << 'EOF'
set -e

echo "================================"
echo "🛑 Stopping notifs container..."
echo "================================"

if docker ps -q --filter "name=seatsteal-notifs" | grep -q .; then
    docker stop seatsteal-notifs
    docker rm seatsteal-notifs
    echo "✅ seatsteal-notifs container stopped and removed"
else
    echo "ℹ️  No seatsteal-notifs container found running"
fi

echo ""
echo "================================"
echo "🛑 Stopping scraper container..."
echo "================================"

if docker ps -q --filter "name=seatsteal-scraper" | grep -q .; then
    docker stop seatsteal-scraper
    docker rm seatsteal-scraper
    echo "✅ seatsteal-scraper container stopped and removed"
else
    echo "ℹ️  No seatsteal-scraper container found running"
fi

echo ""
echo "================================"
echo "✅ All services stopped"
echo "================================"
echo "📊 Current container status:"
docker ps
EOF
else
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=5 ec2-user@"$EC2_HOST" << EOF
set -e

echo "🛑 Stopping and removing $CONTAINER_NAME container..."
if docker ps -q --filter "name=$CONTAINER_NAME" | grep -q .; then
    docker stop "$CONTAINER_NAME"
    docker rm "$CONTAINER_NAME"
    echo "✅ $CONTAINER_NAME container stopped and removed"
else
    echo "ℹ️  No $CONTAINER_NAME container found running"
fi

echo "📊 Current container status:"
docker ps
EOF
fi

echo -e "${GREEN}✅ Container kill script completed!${NC}"
