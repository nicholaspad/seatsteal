#!/bin/bash

# Deploy notifs/scraper services to EC2 instance
# Usage: ./utils/deploy-ec2.sh

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

echo -e "${YELLOW}🚀 EC2 Deployment Script for seatsteal/webapp${NC}"
echo "========================================"

# Check local dependencies
echo -e "${YELLOW}🔍 Checking local dependencies...${NC}"
if ! command -v ssh &> /dev/null; then
    echo -e "${RED}❌ Error: ssh is not installed. Please install OpenSSH client.${NC}"
    exit 1
fi

if ! command -v scp &> /dev/null; then
    echo -e "${RED}❌ Error: scp is not installed. Please install OpenSSH client.${NC}"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo -e "${RED}❌ Error: jq is not installed (required for JSON parsing).${NC}"
    echo "Please install it: brew install jq (macOS) or apt install jq (Linux)"
    exit 1
fi

echo -e "${GREEN}✅ Local dependencies satisfied${NC}"
echo ""

# Menu options
options=("notifs" "scraper" "all (notifs + scraper)")
selected=0

# Function to display menu
display_menu() {
  echo "Select service to deploy:"
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
echo -e "${YELLOW}🚀 EC2 Deployment Script for seatsteal/webapp${NC}"
echo "========================================"
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
        echo -e "${YELLOW}🚀 EC2 Deployment Script for seatsteal/webapp${NC}"
        echo "========================================"
        echo ""
        display_menu
        ;;
      '[B')  # Down arrow
        ((selected++))
        if [ $selected -ge ${#options[@]} ]; then
          selected=0
        fi
        clear
        echo -e "${YELLOW}🚀 EC2 Deployment Script for seatsteal/webapp${NC}"
        echo "========================================"
        echo ""
        display_menu
        ;;
    esac
  elif [[ $key == "" ]]; then
    break
  fi
done

# Set SERVICE and DOCKERFILE based on selection
choice=$((selected + 1))

case $choice in
    1)
        SERVICE="notifs"
        DOCKERFILE="notifs.Dockerfile"
        ;;
    2)
        SERVICE="scraper"
        DOCKERFILE="scraper.Dockerfile"
        ;;
    3)
        SERVICE="all"
        DOCKERFILE=""
        ;;
esac

clear
echo -e "${YELLOW}🚀 EC2 Deployment Script for seatsteal/webapp${NC}"
echo "========================================"
echo ""
echo -e "${GREEN}📦 Selected service: $SERVICE${NC}"

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

echo -e "${GREEN}📡 Preparing EC2 instance...${NC}"

# Ensure seatsteal directory exists on remote before copying files
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=5 ec2-user@"$EC2_HOST" "mkdir -p ~/seatsteal"

echo -e "${GREEN}📄 Copying .env file to EC2...${NC}"
scp -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$REPO_ROOT/.env" ec2-user@"$EC2_HOST":~/seatsteal/.env

echo -e "${GREEN}📡 Connecting to ec2-user@$EC2_HOST...${NC}"

# Execute deployment commands on remote server
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=5 ec2-user@"$EC2_HOST" << EOF
set -e

# Load environment variables from .env
if [[ -f ~/seatsteal/.env ]]; then
    set -a
    source ~/seatsteal/.env
    set +a
fi

# Check if GITHUB_TOKEN is set
if [[ -z "\$GITHUB_TOKEN" ]]; then
    echo "❌ Error: GITHUB_TOKEN not found in .env file"
    echo "Please create a GitHub Personal Access Token and add it to your .env file:"
    echo "  1. Go to https://github.com/settings/tokens"
    echo "  2. Generate a new token with 'repo' scope"
    echo "  3. Add to .env: GITHUB_TOKEN=ghp_xxxxxxxxxxxxx"
    exit 1
fi

# Function to check and install dependencies
setup_dependencies() {
    echo "🔍 Checking and installing remote dependencies..."

    # Detect package manager
    if command -v dnf &> /dev/null; then
        PKG_MGR="sudo dnf"
    elif command -v yum &> /dev/null; then
        PKG_MGR="sudo yum"
    else
        echo "❌ Error: No supported package manager found"
        exit 1
    fi

    # Check and install git
    if ! command -v git &> /dev/null; then
        echo "📦 Installing git..."
        \$PKG_MGR install -y git
    else
        echo "✅ git is already installed"
    fi

    # Check and install docker
    if ! command -v docker &> /dev/null; then
        echo "📦 Installing docker..."
        \$PKG_MGR install -y docker
        sudo systemctl enable docker
        sudo systemctl start docker
        sudo usermod -aG docker \$USER
        echo "⚠️  Added user to docker group. You may need to log out and back in for this to take effect."
    else
        echo "✅ docker is already installed"
        # Ensure docker service is running
        if ! sudo systemctl is-active --quiet docker; then
            echo "🚀 Starting docker service..."
            sudo systemctl start docker
        fi
        # Ensure user is in docker group
        if ! groups | grep -q docker; then
            sudo usermod -aG docker \$USER
            echo "⚠️  Added user to docker group."
        fi
    fi

    echo "✅ All dependencies installed"

    # Clone repository if it doesn't exist
    if [[ ! -d ~/seatsteal/.git ]]; then
        # Back up .env if it exists
        if [[ -f ~/seatsteal/.env ]]; then
            cp ~/seatsteal/.env /tmp/seatsteal.env.backup
        fi

        # Remove directory if it exists but isn't a git repo
        if [[ -d ~/seatsteal ]]; then
            rm -rf ~/seatsteal
        fi

        echo "📥 Cloning seatsteal repository..."
        git clone https://\$GITHUB_TOKEN@github.com/nicholaspad/seatsteal.git ~/seatsteal

        # Restore .env if we backed it up
        if [[ -f /tmp/seatsteal.env.backup ]]; then
            cp /tmp/seatsteal.env.backup ~/seatsteal/.env
            rm /tmp/seatsteal.env.backup
        fi
    else
        echo "✅ Repository already exists, configuring git credentials..."
        cd ~/seatsteal
        git remote set-url origin https://\$GITHUB_TOKEN@github.com/nicholaspad/seatsteal.git
        cd ~
    fi

    echo "✅ All dependencies satisfied"
}

# Run dependency setup
setup_dependencies

# Navigate to project and update code
echo "🔄 Navigating to seatsteal/webapp directory..."
cd ~/seatsteal/webapp

echo "📥 Pulling latest changes..."
cd ~/seatsteal && git pull && cd webapp

echo "📄 Copying .env file to webapp directory..."
cp ../.env .env

# Service-specific deployment
if [[ "$SERVICE" == "all" ]]; then
    # Deploy both services sequentially
    echo "================================"
    echo "🚀 Deploying notifs service..."
    echo "================================"

    echo "🐳 Stopping notifs container if running..."
    sg docker -c "docker stop seatsteal-notifs" || true
    sg docker -c "docker rm seatsteal-notifs" || true

    echo "🏗️  Building notifs Docker image..."
    sg docker -c "docker build --tag \"seatsteal-notifs\" -f \"notifs.Dockerfile\" ."

    echo "🚀 Starting notifs container..."
    sg docker -c "docker run -d \\
        --name \"seatsteal-notifs\" \\
        --env-file .env \\
        \"seatsteal-notifs\""

    echo "✅ notifs deployment completed!"
    echo "📊 Container status:"
    sg docker -c "docker ps --filter \"name=seatsteal-notifs\""

    echo "📋 Recent container logs:"
    sg docker -c "docker logs --tail 20 \"seatsteal-notifs\""

    echo ""
    echo "================================"
    echo "🚀 Deploying scraper service..."
    echo "================================"

    echo "🐳 Stopping scraper container if running..."
    sg docker -c "docker stop seatsteal-scraper" || true
    sg docker -c "docker rm seatsteal-scraper" || true

    echo "🏗️  Building scraper Docker image..."
    sg docker -c "docker build --tag \"seatsteal-scraper\" -f \"scraper.Dockerfile\" ."

    echo "🚀 Starting scraper container..."
    sg docker -c "docker run -d \\
        --name \"seatsteal-scraper\" \\
        --env-file .env \\
        \"seatsteal-scraper\""

    echo "✅ scraper deployment completed!"
    echo "📊 Container status:"
    sg docker -c "docker ps --filter \"name=seatsteal-scraper\""

    echo "📋 Recent container logs:"
    sg docker -c "docker logs --tail 20 \"seatsteal-scraper\""

    echo ""
    echo "================================"
    echo "✅ All services deployed successfully!"
    echo "================================"
    echo "📊 Overall container status:"
    sg docker -c "docker ps"
else
    echo "🐳 Stopping $SERVICE container if running..."
    sg docker -c "docker stop seatsteal-$SERVICE" || true
    sg docker -c "docker rm seatsteal-$SERVICE" || true

    echo "🏗️  Building $SERVICE Docker image..."
    sg docker -c "docker build --tag \"seatsteal-$SERVICE\" -f \"$DOCKERFILE\" ."

    echo "🚀 Starting $SERVICE container..."
    sg docker -c "docker run -d \\
        --name \"seatsteal-$SERVICE\" \\
        --env-file .env \\
        \"seatsteal-$SERVICE\""

    echo "✅ Deployment completed successfully!"
    echo "📊 Container status:"
    sg docker -c "docker ps --filter \"name=seatsteal-$SERVICE\""

    echo "📋 Recent container logs:"
    sg docker -c "docker logs --tail 20 \"seatsteal-$SERVICE\""
fi
EOF

echo -e "${GREEN}✅ Deployment script completed!${NC}"
