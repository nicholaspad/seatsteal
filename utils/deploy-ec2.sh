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

echo -e "${GREEN}✅ Local dependencies satisfied${NC}"

# Prompt for service
echo "Select service to deploy:"
echo "1) notifs"
echo "2) scraper"
echo "3) all (notifs + scraper + redis)"
echo -n "Enter choice (1-3): "
read -r SERVICE_CHOICE

case $SERVICE_CHOICE in
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
    *)
        echo -e "${RED}❌ Error: Invalid choice. Please select 1-3${NC}"
        exit 1
        ;;
esac

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

echo -e "${GREEN}📡 Preparing EC2 instance...${NC}"

# Ensure seatsteal directory exists on remote before copying files
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=5 ec2-user@"$EC2_HOST" "mkdir -p ~/seatsteal"

echo -e "${GREEN}📄 Copying .env file to EC2...${NC}"
scp -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$REPO_ROOT/.env" ec2-user@"$EC2_HOST":~/seatsteal/.env

echo -e "${GREEN}📡 Connecting to ec2-user@$EC2_HOST...${NC}"

# Execute deployment commands on remote server
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=5 ec2-user@"$EC2_HOST" << EOF
set -e

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

    # Check and install docker-compose
    if ! command -v docker-compose &> /dev/null; then
        echo "📦 Installing docker-compose..."
        # Install pip if not available
        if ! command -v pip3 &> /dev/null; then
            \$PKG_MGR install -y python3-pip
        fi
        sudo pip3 install docker-compose
    else
        echo "✅ docker-compose is already installed"
    fi

    # Clone repository if it doesn't exist
    if [[ ! -d ~/seatsteal ]]; then
        echo "📥 Cloning seatsteal repository..."
        git clone https://github.com/nicholaspad/seatsteal.git ~/seatsteal
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
    echo "🐳 Stopping all containers..."
    docker-compose down || true

    echo "🏗️  Building and starting all services (redis, notifs, scraper)..."
    docker-compose up --build -d

    echo "⏳ Waiting for services to start..."
    sleep 5

    echo "✅ Deployment completed successfully!"
    echo "📊 Container status:"
    docker-compose ps

    echo "📋 Recent logs:"
    docker-compose logs --tail=20
else
    echo "🐳 Checking if Redis is running..."
    if ! docker ps | grep -q "seatsteal-redis"; then
        echo "🚀 Starting Redis container..."
        docker-compose up -d redis
        sleep 3
    fi

    echo "🐳 Stopping $SERVICE container if running..."
    docker stop seatsteal-$SERVICE || true
    docker rm seatsteal-$SERVICE || true

    echo "🏗️  Building $SERVICE Docker image..."
    docker build --tag "seatsteal-$SERVICE" -f "$DOCKERFILE" .

    echo "🚀 Starting $SERVICE container..."
    docker run -d \\
        --name "seatsteal-$SERVICE" \\
        --env-file .env \\
        --env REDIS_URL=redis://\$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' seatsteal-redis):6379 \\
        --network bridge \\
        "seatsteal-$SERVICE"

    echo "✅ Deployment completed successfully!"
    echo "📊 Container status:"
    docker ps --filter "name=seatsteal-$SERVICE"

    echo "📋 Recent container logs:"
    docker logs --follow --tail 20 "seatsteal-$SERVICE"
fi
EOF

echo -e "${GREEN}✅ Deployment script completed!${NC}"
