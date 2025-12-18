#!/bin/bash

# SeatSteal Management Script
# Main entry point for deployment and service management

set -e  # Exit on error

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
