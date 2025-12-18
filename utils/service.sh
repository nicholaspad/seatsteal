#!/bin/bash

# SeatSteal EC2 Service Management Script
# Unified interface for managing EC2 services

set -e  # Exit on error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to display menu
display_menu() {
  echo "=========================================="
  echo "  SeatSteal EC2 Service Management"
  echo "=========================================="
  echo ""
  echo "What would you like to do?"
  echo ""
  echo "  1) Deploy services"
  echo "  2) View service logs"
  echo "  3) Kill services"
  echo "  4) SSH into instance"
  echo "  5) Spin up instance"
  echo "  6) Terminate instance"
  echo ""
  echo "  0) Back"
  echo ""
}

# Main loop
while true; do
  # Clear screen and show menu
  clear
  display_menu

  # Read user input
  read -r -p "Enter choice: " choice

  case $choice in
    1)
      clear
      echo "=========================================="
      echo "  SeatSteal EC2 Service Management"
      echo "=========================================="
      echo ""
      echo "🚀 Deploying services to EC2..."
      echo ""
      "$SCRIPT_DIR/deploy-ec2.sh"
      echo ""
      echo "=========================================="
      echo "  Operation finished!"
      echo "=========================================="
      echo ""
      read -r -p "Press Enter to continue..."
      ;;
    2)
      clear
      echo "=========================================="
      echo "  SeatSteal EC2 Service Management"
      echo "=========================================="
      echo ""
      echo "📋 Viewing service logs from EC2..."
      echo ""
      "$SCRIPT_DIR/logs-ec2.sh"
      echo ""
      echo "=========================================="
      echo "  Operation finished!"
      echo "=========================================="
      echo ""
      read -r -p "Press Enter to continue..."
      ;;
    3)
      clear
      echo "=========================================="
      echo "  SeatSteal EC2 Service Management"
      echo "=========================================="
      echo ""
      echo "🛑 Killing services on EC2..."
      echo ""
      "$SCRIPT_DIR/kill-containers-ec2.sh"
      echo ""
      echo "=========================================="
      echo "  Operation finished!"
      echo "=========================================="
      echo ""
      read -r -p "Press Enter to continue..."
      ;;
    4)
      clear
      echo "=========================================="
      echo "  SeatSteal EC2 Service Management"
      echo "=========================================="
      echo ""
      echo "🔑 SSHing into EC2 instance..."
      echo ""
      "$SCRIPT_DIR/login-ec2.sh"
      echo ""
      echo "=========================================="
      echo "  Operation finished!"
      echo "=========================================="
      echo ""
      read -r -p "Press Enter to continue..."
      ;;
    5)
      clear
      INSTANCE_TYPE=$("$SCRIPT_DIR/select-instance-type.sh")
      if [ -z "$INSTANCE_TYPE" ]; then
        clear
        echo "=========================================="
        echo "  SeatSteal EC2 Service Management"
        echo "=========================================="
        echo ""
        echo "Instance type selection cancelled."
        echo ""
        read -r -p "Press Enter to continue..."
      else
        clear
        echo "=========================================="
        echo "  SeatSteal EC2 Service Management"
        echo "=========================================="
        echo ""
        echo "🚀 Spinning up new EC2 instance ($INSTANCE_TYPE)..."
        echo ""
        "$SCRIPT_DIR/spin-up-ec2.sh" "$INSTANCE_TYPE"
        echo ""
        echo "=========================================="
        echo "  Operation finished!"
        echo "=========================================="
        echo ""
        read -r -p "Press Enter to continue..."
      fi
      ;;
    6)
      clear
      echo "=========================================="
      echo "  SeatSteal EC2 Service Management"
      echo "=========================================="
      echo ""
      echo "🛑 Terminating EC2 instance..."
      echo ""
      "$SCRIPT_DIR/terminate-ec2.sh"
      echo ""
      echo "=========================================="
      echo "  Operation finished!"
      echo "=========================================="
      echo ""
      read -r -p "Press Enter to continue..."
      ;;
    0)
      # Go back to parent menu
      exit 0
      ;;
    *)
      echo ""
      echo "Invalid option. Please try again."
      sleep 1
      ;;
  esac
done
