#!/bin/bash

# SeatSteal Local Utilities Script
# Local development tools for managing scrapers and data

set -e  # Exit on error

# Menu options
options=("Run scraper" "Add college & scraper" "Clear college course data" "Get term codes")
selected=0  # Default to first option (index 0)

# Function to display menu
display_menu() {
  echo "=========================================="
  echo "  SeatSteal Local Utils"
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
echo "  SeatSteal Local Utils"
echo "=========================================="
echo ""

# Execute based on selection
choice=$((selected + 1))

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

case $choice in
  1)
    echo "Run Scraper"
    echo ""
    echo "Enter the college short name (e.g., princeton, cornell, umd):"
    read -r college
    if [ -z "$college" ]; then
      echo "Error: College name cannot be empty"
      exit 1
    fi
    echo ""
    echo "Running scraper for $college..."
    echo ""
    cd "$PROJECT_DIR/webapp" && source venv/bin/activate && python scraper/run_scraper.py run --college "$college"
    ;;
  2)
    echo "Add College & Scraper"
    echo ""
    cd "$PROJECT_DIR/webapp" && source venv/bin/activate && python scripts/add_college_scraper.py
    ;;
  3)
    echo "Clear College Course Data"
    echo ""
    echo "Enter the college short name (e.g., princeton, cornell, umd):"
    read -r college
    if [ -z "$college" ]; then
      echo "Error: College name cannot be empty"
      exit 1
    fi
    echo ""
    echo "WARNING: This will delete ALL course data for $college!"
    echo "Are you sure? (yes/no):"
    read -r confirm
    if [ "$confirm" = "yes" ]; then
      cd "$PROJECT_DIR/webapp" && source venv/bin/activate && python scripts/clear_college.py --college "$college" --confirm
    else
      echo "Operation cancelled."
    fi
    ;;
  4)
    echo "Term Codes for All Colleges"
    echo ""
    cd "$PROJECT_DIR/webapp" && source venv/bin/activate && python scripts/term_codes_table.py
    ;;
esac

echo ""
echo "=========================================="
echo "  Operation finished!"
echo "=========================================="
