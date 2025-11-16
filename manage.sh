#!/bin/bash

# SeatSteal Management Script
# Main entry point for deployment and service management

set -e  # Exit on error

# Menu options
options=("Deploy seatsteal (Vercel)" "Manage EC2 services" "Local utils")
selected=0  # Default to "Deploy seatsteal" (index 0)

# Function to display menu
display_menu() {
  echo "=========================================="
  echo "  SeatSteal Management"
  echo "=========================================="
  echo ""
  echo "What would you like to do?"
  echo "(Use ↑/↓ arrows to navigate, Enter to select, q to exit)"
  echo ""

  for i in "${!options[@]}"; do
    if [ $i -eq $selected ]; then
      echo "  → ${options[$i]}"
    else
      echo "    ${options[$i]}"
    fi
  done
}

# Main loop - allows returning to menu after submenu exits
while true; do
  # Clear screen and show menu
  clear
  display_menu

  # Read arrow keys
  while true; do
    # Read a single character
    read -rsn1 key

    # Check if it's an escape sequence (arrow keys start with ESC)
    if [[ $key == $'\x1b' ]]; then
      # Try to read more characters (arrow keys send ESC [ A/B/C/D)
      read -rsn2 rest
      case $rest in
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
        *)
          # Standalone escape key or unknown sequence - exit
          clear
          echo "Exiting..."
          exit 0
          ;;
      esac
    elif [[ $key == "" ]]; then
      # Enter key pressed
      break
    elif [[ $key == "q" ]]; then
      # q key pressed - exit
      clear
      echo "Exiting..."
      exit 0
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
    3)
      ./utils/local.sh
      ;;
  esac
done
