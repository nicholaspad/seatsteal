#!/bin/bash

# Select EC2 Instance Type
# Displays instance type options and returns selected type to stdout

set -e  # Exit on error

# Function to display menu (output to /dev/tty to avoid command substitution capture)
display_menu() {
  echo "==========================================" >/dev/tty
  echo "  Select EC2 Instance Type" >/dev/tty
  echo "==========================================" >/dev/tty
  echo "" >/dev/tty
  echo "Choose an instance type:" >/dev/tty
  echo "" >/dev/tty
  echo "  1) t4g.nano  (2 vCPUs, 0.5 GB)  - ~\$3/month" >/dev/tty
  echo "  2) t4g.micro (2 vCPUs, 1.0 GB)  - ~\$6/month" >/dev/tty
  echo "  3) t4g.small (2 vCPUs, 2.0 GB)  - ~\$12/month" >/dev/tty
  echo "" >/dev/tty
  echo "  0) Cancel" >/dev/tty
  echo "" >/dev/tty
}

# Clear screen and show menu (redirect to /dev/tty)
clear >/dev/tty
display_menu

# Read user input
echo -n "Enter choice: " >/dev/tty
read -r choice

case $choice in
  1)
    echo "t4g.nano"
    ;;
  2)
    echo "t4g.micro"
    ;;
  3)
    echo "t4g.small"
    ;;
  0)
    # Cancel - output nothing
    exit 0
    ;;
  *)
    echo "Invalid option." >/dev/tty
    exit 1
    ;;
esac
