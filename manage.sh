#!/bin/bash

# SeatSteal Management Script
# Main entry point for deployment and service management

set -e  # Exit on error

# Menu options
options=("Deploy seatsteal (Vercel)" "Manage EC2 services")
selected=0  # Default to "Deploy seatsteal" (index 0)

# Function to display menu
display_menu() {
  echo "=========================================="
  echo "  SeatSteal Management"
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

# Execute based on selection
choice=$((selected + 1))

case $choice in
  1)
    ./utils/deploy.sh
    ;;
  2)
    ./utils/service.sh
    ;;
esac
