#!/bin/bash

# Terminate EC2 instance and clean up resources
# Usage: ./utils/terminate-ec2.sh

set -e  # Exit on any error

# Disable AWS CLI pager to avoid interactive prompts
export AWS_PAGER=""

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

# AWS Configuration
REGION="us-east-1"
KEY_NAME="seatsteal"
SECURITY_GROUP_NAME="seatsteal-sg"

echo -e "${YELLOW}🛑 EC2 Instance Termination Script${NC}"
echo "========================================"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ Error: AWS CLI is not installed.${NC}"
    exit 1
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ Error: AWS CLI is not configured with credentials.${NC}"
    exit 1
fi

# Check if jq is installed for JSON parsing
if ! command -v jq &> /dev/null; then
    echo -e "${RED}❌ Error: jq is not installed (required for JSON parsing).${NC}"
    echo "Please install it: brew install jq (macOS) or apt install jq (Linux)"
    exit 1
fi

# First, try to sync credentials from Supabase (in case local files were wiped)
echo -e "${YELLOW}🔍 Checking for existing instance credentials...${NC}"
source "$SCRIPT_DIR/ec2-credentials.sh"
sync_credentials || true
echo ""

# Check if ec2-host.json file exists
if [[ ! -f "$EC2_HOST_FILE" ]]; then
    echo -e "${RED}❌ Error: EC2 host file not found at $EC2_HOST_FILE${NC}"
    echo "No instance to terminate."
    exit 1
fi

# Read instance info from JSON file
INSTANCE_ID=$(jq -r '.instance_id // empty' "$EC2_HOST_FILE" 2>/dev/null || echo "")
PUBLIC_DNS=$(jq -r '.public_dns // empty' "$EC2_HOST_FILE" 2>/dev/null || echo "")

if [[ -z "$INSTANCE_ID" ]]; then
    echo -e "${RED}❌ Error: Could not read instance ID from $EC2_HOST_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}📋 Found instance: $INSTANCE_ID${NC}"
if [[ -n "$PUBLIC_DNS" ]]; then
    echo -e "${GREEN}📋 Public DNS: $PUBLIC_DNS${NC}"
fi
echo ""

# Step 1: Check instance status
echo -e "${YELLOW}🔍 Checking instance status...${NC}"

INSTANCE_STATE=$(aws ec2 describe-instances \
    --region "$REGION" \
    --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].State.Name' \
    --output text 2>/dev/null || echo "not-found")

if [[ "$INSTANCE_STATE" == "not-found" || "$INSTANCE_STATE" == "None" || "$INSTANCE_STATE" == "terminated" ]]; then
    echo -e "${YELLOW}⚠️  Warning: Instance $INSTANCE_ID is already terminated or not found.${NC}"
    echo -e "${YELLOW}Proceeding with cleanup of remaining resources...${NC}"
    echo ""

    SKIP_TERMINATION=true
else
    echo -e "${GREEN}✅ Instance state: $INSTANCE_STATE${NC}"
    echo ""

    # Step 2: Terminate instance
    echo -e "${YELLOW}🛑 Terminating instance...${NC}"

    aws ec2 terminate-instances \
        --region "$REGION" \
        --instance-ids "$INSTANCE_ID" > /dev/null

    echo -e "${GREEN}✅ Termination initiated${NC}"
    echo ""

    # Step 3: Wait for instance to terminate
    echo -e "${YELLOW}⏳ Waiting for instance to terminate (this may take a minute)...${NC}"

    aws ec2 wait instance-terminated \
        --region "$REGION" \
        --instance-ids "$INSTANCE_ID"

    echo -e "${GREEN}✅ Instance terminated${NC}"
    echo ""
fi

# Step 4: Delete security group
echo -e "${YELLOW}🔒 Deleting security group...${NC}"

# Get security group ID
SG_ID=$(aws ec2 describe-security-groups \
    --region "$REGION" \
    --filters "Name=group-name,Values=$SECURITY_GROUP_NAME" \
    --query 'SecurityGroups[0].GroupId' \
    --output text 2>/dev/null || echo "None")

if [[ "$SG_ID" != "None" && -n "$SG_ID" ]]; then
    # Sometimes need to wait a bit for AWS to release the security group
    sleep 5

    aws ec2 delete-security-group \
        --region "$REGION" \
        --group-id "$SG_ID" 2>/dev/null || echo -e "${YELLOW}⚠️  Could not delete security group (may still be in use)${NC}"

    echo -e "${GREEN}✅ Security group deleted${NC}"
else
    echo -e "${YELLOW}⚠️  Security group not found (may already be deleted)${NC}"
fi

echo ""

# Step 5: Delete key pair
echo -e "${YELLOW}🔑 Deleting key pair...${NC}"

aws ec2 delete-key-pair \
    --region "$REGION" \
    --key-name "$KEY_NAME" 2>/dev/null || echo -e "${YELLOW}⚠️  Key pair not found in AWS (may already be deleted)${NC}"

echo -e "${GREEN}✅ Key pair deleted from AWS${NC}"
echo ""

# Step 6: Deactivate credentials in Supabase
echo -e "${YELLOW}🗑️  Deactivating credentials in Supabase...${NC}"
source "$SCRIPT_DIR/ec2-credentials.sh"
if delete_credentials; then
    echo -e "${GREEN}✅ Credentials deactivated in Supabase${NC}"
else
    echo -e "${YELLOW}⚠️  Could not deactivate credentials in Supabase${NC}"
fi
echo ""

# Step 7: Delete local files
echo -e "${YELLOW}🗑️  Cleaning up local files...${NC}"

if [[ -f "$PEM_FILE" ]]; then
    rm -f "$PEM_FILE"
    echo -e "${GREEN}✅ Deleted: $PEM_FILE${NC}"
fi

if [[ -f "$EC2_HOST_FILE" ]]; then
    rm "$EC2_HOST_FILE"
    echo -e "${GREEN}✅ Deleted: $EC2_HOST_FILE${NC}"
fi

echo ""

# Display summary
echo "=========================================="
echo -e "${GREEN}✅ EC2 Instance Successfully Terminated!${NC}"
echo "=========================================="
echo ""
echo "Cleaned up:"
if [[ -n "$INSTANCE_ID" ]]; then
    echo "  ✅ Instance: $INSTANCE_ID"
fi
echo "  ✅ Security Group: $SECURITY_GROUP_NAME"
echo "  ✅ Key Pair: $KEY_NAME"
echo "  ✅ Local PEM file: seatsteal.pem"
echo "  ✅ EC2 host file cleared"
echo ""
