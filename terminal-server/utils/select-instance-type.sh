#!/bin/bash

# Select EC2 Instance Type
# Displays instance type options and returns selected type to stdout

set -e  # Exit on error

# Instance type options with specifications
instance_types=(
  "t4g.nano  (2 vCPUs, 0.5 GB)  - ~\$3/month"
  "t4g.micro (2 vCPUs, 1.0 GB)  - ~\$6/month"
  "t4g.small (2 vCPUs, 2.0 GB)  - ~\$12/month"
)

# Instance type codes (what gets returned)
type_codes=("t4g.nano" "t4g.micro" "t4g.small")

selected=0  # Default to t4g.nano (index 0)

# Function to display menu (output to /dev/tty to avoid command substitution capture)
display_menu() {
  echo "==========================================" >/dev/tty
  echo "  Select EC2 Instance Type" >/dev/tty
  echo "==========================================" >/dev/tty
  echo "" >/dev/tty
  echo "Choose an instance type:" >/dev/tty
  echo "(Use ↑/↓ arrows to navigate, Enter to select)" >/dev/tty
  echo "" >/dev/tty

  for i in "${!instance_types[@]}"; do
    if [ $i -eq $selected ]; then
      echo "  → ${instance_types[$i]}" >/dev/tty
    else
      echo "    ${instance_types[$i]}" >/dev/tty
    fi
  done
}

# Clear screen and show menu (redirect to /dev/tty)
clear >/dev/tty
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
          selected=$((${#instance_types[@]} - 1))
        fi
        clear >/dev/tty
        display_menu
        ;;
      '[B')  # Down arrow
        ((selected++))
        if [ $selected -ge ${#instance_types[@]} ]; then
          selected=0
        fi
        clear >/dev/tty
        display_menu
        ;;
      *)
        # Standalone escape key or unknown sequence - exit without output
        exit 0
        ;;
    esac
  elif [[ $key == "" ]]; then
    # Enter key pressed - output selected type code to stdout (for command substitution)
    echo "${type_codes[$selected]}"
    exit 0
  fi
done
