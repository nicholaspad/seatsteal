#!/bin/bash

# SeatSteal Deployment Script
# Deploys frontend and/or backend to Vercel

set -e  # Exit on error

# Menu options
options=("Both frontend and backend" "Frontend only (seatsteal)" "Backend only (webapp)")
selected=0  # Default to "Both" (index 0)

# Function to display menu
display_menu() {
  echo "=========================================="
  echo "  SeatSteal Deployment"
  echo "=========================================="
  echo ""
  echo "What would you like to deploy?"
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

# Clear screen before deployment
clear
echo "=========================================="
echo "  SeatSteal Deployment"
echo "=========================================="
echo ""

# Execute based on selection
choice=$((selected + 1))

case $choice in
  1)
    echo ""
    echo "🚀 Deploying both frontend and backend to Vercel..."
    echo ""

    # Deploy backend first
    echo "📦 Starting backend deployment..."
    cd webapp && vercel --prod
    echo "✅ Backend deployment complete!"
    echo ""

    # Then deploy frontend
    echo "📦 Starting frontend deployment..."
    cd ../seatsteal && vercel --prod
    echo "✅ Frontend deployment complete!"
    echo ""

    echo "✅ All deployments complete!"
    ;;
  2)
    echo ""
    echo "🚀 Deploying frontend to Vercel..."
    cd seatsteal && vercel --prod
    echo "✅ Frontend deployment complete!"
    ;;
  3)
    echo ""
    echo "🚀 Deploying backend to Vercel..."
    cd webapp && vercel --prod
    echo "✅ Backend deployment complete!"
    ;;
esac

echo ""
echo "=========================================="
echo "  Deployment finished!"
echo "=========================================="
