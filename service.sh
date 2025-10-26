#!/bin/bash

# SeatSteal EC2 Service Management Script
# Unified interface for managing EC2 services

set -e  # Exit on error

# Menu options
options=("Deploy services" "View service logs" "Kill services" "SSH into instance")
selected=0  # Default to "Deploy services" (index 0)

# Function to display menu
display_menu() {
  echo "=========================================="
  echo "  SeatSteal EC2 Service Management"
  echo "=========================================="
  echo ""
  echo "What would you like to do?"
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
display_menu

# Read arrow keys
while true; do
  # Read a single character
  read -rsn1 key

  # Check if it's an escape sequence (arrow keys start with ESC)
  if [[ $key == $'\x1b' ]]; then
    read -rsn2 key  # Read the rest of the escape sequence
    case $key in
      '[A')  # Up arrow
        ((selected--))
        if [ $selected -lt 0 ]; then
          selected=$((${#options[@]} - 1))
        fi
        clear
        display_menu
        ;;
      '[B')  # Down arrow
        ((selected++))
        if [ $selected -ge ${#options[@]} ]; then
          selected=0
        fi
        clear
        display_menu
        ;;
    esac
  elif [[ $key == "" ]]; then
    # Enter key pressed
    break
  fi
done

# Clear screen before execution
clear
echo "=========================================="
echo "  SeatSteal EC2 Service Management"
echo "=========================================="
echo ""

# Execute based on selection
choice=$((selected + 1))

case $choice in
  1)
    echo ""
    echo "🚀 Deploying services to EC2..."
    echo ""
    ./utils/deploy-ec2.sh
    ;;
  2)
    echo ""
    echo "📋 Viewing service logs from EC2..."
    echo ""
    ./utils/logs-ec2.sh
    ;;
  3)
    echo ""
    echo "🛑 Killing services on EC2..."
    echo ""
    ./utils/kill-containers-ec2.sh
    ;;
  4)
    echo ""
    echo "🔑 SSHing into EC2 instance..."
    echo ""
    ./utils/login-ec2.sh
    ;;
esac

echo ""
echo "=========================================="
echo "  Operation finished!"
echo "=========================================="
