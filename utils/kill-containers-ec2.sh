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

# Prompt for service
echo "Select service to kill:"
echo "1) notifs"
echo "2) scraper"
echo "3) redis"
echo "4) all (stop docker-compose)"
echo -n "Enter choice (1-4): "
read -r SERVICE_CHOICE

case $SERVICE_CHOICE in
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
    *)
        echo -e "${RED}❌ Error: Invalid choice. Please select 1-4${NC}"
        exit 1
        ;;
esac

echo -e "${GREEN}🎯 Selected service: $SERVICE${NC}"

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

# Read EC2 host from file
EC2_HOST_FILE="$SCRIPT_DIR/ec2-host"
if [[ ! -f "$EC2_HOST_FILE" ]]; then
    echo -e "${RED}❌ Error: EC2 host file not found at $EC2_HOST_FILE${NC}"
    exit 1
fi

EC2_HOST=$(cat "$EC2_HOST_FILE" | tr -d '\n\r')
if [[ -z "$EC2_HOST" ]]; then
    echo -e "${RED}❌ Error: EC2 host file is empty${NC}"
    exit 1
fi

echo -e "${GREEN}📋 Using EC2 host: $EC2_HOST${NC}"

echo -e "${GREEN}📡 Connecting to ec2-user@$EC2_HOST...${NC}"

# Kill selected container(s)
if [[ "$SERVICE" == "all" ]]; then
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=5 ec2-user@"$EC2_HOST" << 'EOF'
set -e

echo "🛑 Stopping all services via docker-compose..."
cd ~/seatsteal/webapp
docker-compose down

echo "✅ All services stopped"
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
