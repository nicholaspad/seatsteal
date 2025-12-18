#!/bin/bash

# Spin up EC2 instance (t4g.nano)
# Usage: ./utils/spin-up-ec2.sh [instance_type]

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
EC2_HOST_FILE="$SCRIPT_DIR/ec2-host.json"
PEM_FILE="$REPO_ROOT/seatsteal.pem"

# Accept instance type as parameter, default to t4g.nano
INSTANCE_TYPE="${1:-t4g.nano}"

# Validate instance type
case "$INSTANCE_TYPE" in
  t4g.nano|t4g.micro|t4g.small)
    ;;
  *)
    echo -e "${RED}❌ Error: Invalid instance type '$INSTANCE_TYPE'${NC}"
    echo "Valid types: t4g.nano, t4g.micro, t4g.small"
    exit 1
    ;;
esac

# AWS Configuration
REGION="us-east-1"
KEY_NAME="seatsteal"
SECURITY_GROUP_NAME="seatsteal-sg"
INSTANCE_TAG_NAME="seatsteal"

echo -e "${YELLOW}🚀 EC2 Instance Spin-Up Script${NC}"
echo "========================================"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ Error: AWS CLI is not installed.${NC}"
    echo "Please install it: https://aws.amazon.com/cli/"
    exit 1
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ Error: AWS CLI is not configured with credentials.${NC}"
    echo "Please run: aws configure"
    exit 1
fi

echo -e "${GREEN}✅ AWS CLI is configured${NC}"
echo ""

# Check if an instance already exists
if [[ -f "$EC2_HOST_FILE" ]]; then
    echo -e "${YELLOW}🔍 Checking for existing instance...${NC}"

    # Check if jq is installed for JSON parsing
    if ! command -v jq &> /dev/null; then
        echo -e "${RED}❌ Error: jq is not installed (required for JSON parsing).${NC}"
        echo "Please install it: brew install jq (macOS) or apt install jq (Linux)"
        exit 1
    fi

    # Try to read existing instance ID from JSON
    EXISTING_INSTANCE_ID=$(jq -r '.instance_id // empty' "$EC2_HOST_FILE" 2>/dev/null || echo "")

    if [[ -n "$EXISTING_INSTANCE_ID" ]]; then
        # Check if instance still exists and its state
        INSTANCE_STATE=$(aws ec2 describe-instances \
            --region "$REGION" \
            --instance-ids "$EXISTING_INSTANCE_ID" \
            --query 'Reservations[0].Instances[0].State.Name' \
            --output text 2>/dev/null || echo "terminated")

        if [[ "$INSTANCE_STATE" != "terminated" && "$INSTANCE_STATE" != "None" ]]; then
            EXISTING_DNS=$(jq -r '.public_dns // empty' "$EC2_HOST_FILE" 2>/dev/null || echo "")

            echo ""
            echo "=========================================="
            echo -e "${YELLOW}⚠️  Instance Already Exists!${NC}"
            echo "=========================================="
            echo ""
            echo "Instance Details:"
            echo "  Instance ID:  $EXISTING_INSTANCE_ID"
            echo "  State:        $INSTANCE_STATE"
            echo "  Public DNS:   $EXISTING_DNS"
            echo ""
            echo "To create a new instance, first terminate the existing one:"
            echo "  ./service.sh → Terminate instance"
            echo ""
            exit 0
        else
            echo -e "${YELLOW}⚠️  Previous instance is terminated. Creating new one...${NC}"
            echo ""
        fi
    fi
fi

# Step 1: Create or get security group
echo -e "${YELLOW}🔒 Setting up security group...${NC}"

# Check if security group exists
SG_ID=$(aws ec2 describe-security-groups \
    --region "$REGION" \
    --filters "Name=group-name,Values=$SECURITY_GROUP_NAME" \
    --query 'SecurityGroups[0].GroupId' \
    --output text 2>/dev/null || echo "None")

if [[ "$SG_ID" == "None" ]]; then
    echo "Creating new security group: $SECURITY_GROUP_NAME"

    # Create security group
    SG_ID=$(aws ec2 create-security-group \
        --region "$REGION" \
        --group-name "$SECURITY_GROUP_NAME" \
        --description "Security group for SeatSteal EC2 instance" \
        --query 'GroupId' \
        --output text)

    # Add inbound rules
    # SSH (22)
    aws ec2 authorize-security-group-ingress \
        --region "$REGION" \
        --group-id "$SG_ID" \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0 \
        --group-name "$SECURITY_GROUP_NAME" > /dev/null

    # HTTP (80)
    aws ec2 authorize-security-group-ingress \
        --region "$REGION" \
        --group-id "$SG_ID" \
        --protocol tcp \
        --port 80 \
        --cidr 0.0.0.0/0 \
        --group-name "$SECURITY_GROUP_NAME" > /dev/null

    # HTTPS (443)
    aws ec2 authorize-security-group-ingress \
        --region "$REGION" \
        --group-id "$SG_ID" \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0 \
        --group-name "$SECURITY_GROUP_NAME" > /dev/null

    # API (5000)
    aws ec2 authorize-security-group-ingress \
        --region "$REGION" \
        --group-id "$SG_ID" \
        --protocol tcp \
        --port 5000 \
        --cidr 0.0.0.0/0 \
        --group-name "$SECURITY_GROUP_NAME" > /dev/null

    echo -e "${GREEN}✅ Security group created: $SG_ID${NC}"
else
    echo -e "${GREEN}✅ Using existing security group: $SG_ID${NC}"
fi

echo ""

# Step 2: Create key pair
echo -e "${YELLOW}🔑 Setting up key pair...${NC}"

# Delete old key pair from AWS if it exists
aws ec2 delete-key-pair \
    --region "$REGION" \
    --key-name "$KEY_NAME" &> /dev/null || true

# Delete old local PEM file if it exists
if [[ -f "$PEM_FILE" ]]; then
    rm -f "$PEM_FILE"
fi

# Create new key pair and save to file
aws ec2 create-key-pair \
    --region "$REGION" \
    --key-name "$KEY_NAME" \
    --query 'KeyMaterial' \
    --output text > "$PEM_FILE"

# Set proper permissions
chmod 400 "$PEM_FILE"

echo -e "${GREEN}✅ Key pair created and saved to: $PEM_FILE${NC}"
echo ""

# Step 3: Find latest Amazon Linux 2023 ARM64 AMI
echo -e "${YELLOW}🔍 Finding latest Amazon Linux 2023 ARM64 AMI...${NC}"

AMI_ID=$(aws ec2 describe-images \
    --region "$REGION" \
    --owners amazon \
    --filters "Name=name,Values=al2023-ami-2023.*-kernel-*-arm64" \
              "Name=state,Values=available" \
    --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
    --output text)

if [[ -z "$AMI_ID" || "$AMI_ID" == "None" ]]; then
    echo -e "${RED}❌ Error: Could not find Amazon Linux 2023 ARM64 AMI${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Using AMI: $AMI_ID${NC}"
echo ""

# Step 4: Launch EC2 instance
echo -e "${YELLOW}🚀 Launching EC2 instance ($INSTANCE_TYPE)...${NC}"

INSTANCE_ID=$(aws ec2 run-instances \
    --region "$REGION" \
    --image-id "$AMI_ID" \
    --instance-type "$INSTANCE_TYPE" \
    --key-name "$KEY_NAME" \
    --security-group-ids "$SG_ID" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_TAG_NAME}]" \
    --query 'Instances[0].InstanceId' \
    --output text)

echo -e "${GREEN}✅ Instance launched: $INSTANCE_ID${NC}"
echo ""

# Step 5: Wait for instance to be running
echo -e "${YELLOW}⏳ Waiting for instance to be running...${NC}"

aws ec2 wait instance-running \
    --region "$REGION" \
    --instance-ids "$INSTANCE_ID"

echo -e "${GREEN}✅ Instance is now running${NC}"
echo ""

# Step 6: Get public DNS name
echo -e "${YELLOW}🌐 Getting public DNS name...${NC}"

PUBLIC_DNS=$(aws ec2 describe-instances \
    --region "$REGION" \
    --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].PublicDnsName' \
    --output text)

if [[ -z "$PUBLIC_DNS" || "$PUBLIC_DNS" == "None" ]]; then
    echo -e "${RED}❌ Error: Could not get public DNS name${NC}"
    exit 1
fi

# Step 7: Write instance info to JSON file
cat > "$EC2_HOST_FILE" << JSONEOF
{
  "instance_id": "$INSTANCE_ID",
  "public_dns": "$PUBLIC_DNS",
  "region": "$REGION",
  "instance_type": "$INSTANCE_TYPE"
}
JSONEOF

echo -e "${GREEN}✅ Public DNS: $PUBLIC_DNS${NC}"
echo -e "${GREEN}✅ Instance info saved to: $EC2_HOST_FILE${NC}"
echo ""

# Step 8: Store credentials in Supabase for persistence across terminal-server redeployments
echo -e "${YELLOW}📦 Storing credentials in Supabase...${NC}"
source "$SCRIPT_DIR/ec2-credentials.sh"
if store_credentials "$PEM_FILE" "$EC2_HOST_FILE"; then
    echo -e "${GREEN}✅ Credentials stored in Supabase${NC}"
else
    echo -e "${YELLOW}⚠️  Could not store credentials in Supabase (local files still work)${NC}"
fi
echo ""

# Display summary
echo "=========================================="
echo -e "${GREEN}✅ EC2 Instance Successfully Created!${NC}"
echo "=========================================="
echo ""
echo "Instance Details:"
echo "  Instance ID:  $INSTANCE_ID"
echo "  Instance Type: $INSTANCE_TYPE"
echo "  Public DNS:   $PUBLIC_DNS"
echo "  Region:       $REGION"
echo "  Key Pair:     $PEM_FILE"
echo ""
echo "To connect:"
echo "  ssh -i $PEM_FILE ec2-user@$PUBLIC_DNS"
echo ""
echo "Or use:"
echo "  ./service.sh → SSH into instance"
echo ""
