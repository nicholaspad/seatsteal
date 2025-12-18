#!/bin/bash

# SeatSteal Local Utilities Script
# Local development tools for managing scrapers and data

set -e  # Exit on error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Function to display menu
display_menu() {
  echo "=========================================="
  echo "  SeatSteal Local Utils"
  echo "=========================================="
  echo ""
  echo "What would you like to do?"
  echo ""
  echo "  1) Run scraper"
  echo "  2) Add college & scraper"
  echo "  3) Clear college course data"
  echo "  4) Get term codes"
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
      echo "  Run Scraper"
      echo "=========================================="
      echo ""
      echo "Enter the college short name (e.g., princeton, cornell, umd):"
      read -r college
      if [ -z "$college" ]; then
        echo "Error: College name cannot be empty"
        echo ""
        read -r -p "Press Enter to continue..."
        continue
      fi
      echo ""
      echo "Running scraper for $college..."
      echo ""
      cd "$PROJECT_DIR/webapp" && (source venv/bin/activate 2>/dev/null || true) && python scraper/run_scraper.py run --college "$college"
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
      echo "  Add College & Scraper"
      echo "=========================================="
      echo ""
      cd "$PROJECT_DIR/webapp" && (source venv/bin/activate 2>/dev/null || true) && python scripts/add_college_scraper.py
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
      echo "  Clear College Course Data"
      echo "=========================================="
      echo ""
      echo "Enter the college short name (e.g., princeton, cornell, umd):"
      read -r college
      if [ -z "$college" ]; then
        echo "Error: College name cannot be empty"
        echo ""
        read -r -p "Press Enter to continue..."
        continue
      fi
      echo ""
      echo "WARNING: This will delete ALL course data for $college!"
      echo "Are you sure? (yes/no):"
      read -r confirm
      if [ "$confirm" = "yes" ]; then
        cd "$PROJECT_DIR/webapp" && (source venv/bin/activate 2>/dev/null || true) && python scripts/clear_college.py --college "$college" --confirm
      else
        echo "Operation cancelled."
      fi
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
      echo "  Term Codes for All Colleges"
      echo "=========================================="
      echo ""
      cd "$PROJECT_DIR/webapp" && (source venv/bin/activate 2>/dev/null || true) && python scripts/term_codes_table.py
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
