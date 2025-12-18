#!/bin/bash

# SeatSteal Deployment Script
# Deploys frontend and/or backend to Vercel

set -e  # Exit on error

# Function to display menu
display_menu() {
  echo "=========================================="
  echo "  SeatSteal Deployment"
  echo "=========================================="
  echo ""
  echo "What would you like to deploy?"
  echo ""
  echo "  1) Both frontend and backend"
  echo "  2) Frontend only (seatsteal)"
  echo "  3) Backend only (webapp)"
  echo ""
  echo "  0) Back"
  echo ""
}

# Clear screen and show menu
clear
display_menu

# Read user input
read -r -p "Enter choice: " choice

case $choice in
  1)
    clear
    echo "=========================================="
    echo "  SeatSteal Deployment"
    echo "=========================================="
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
    clear
    echo "=========================================="
    echo "  SeatSteal Deployment"
    echo "=========================================="
    echo ""
    echo "🚀 Deploying frontend to Vercel..."
    cd seatsteal && vercel --prod
    echo "✅ Frontend deployment complete!"
    ;;
  3)
    clear
    echo "=========================================="
    echo "  SeatSteal Deployment"
    echo "=========================================="
    echo ""
    echo "🚀 Deploying backend to Vercel..."
    cd webapp && vercel --prod
    echo "✅ Backend deployment complete!"
    ;;
  0)
    # Go back to parent menu
    exit 0
    ;;
  *)
    echo ""
    echo "Invalid option."
    exit 1
    ;;
esac

echo ""
echo "=========================================="
echo "  Deployment finished!"
echo "=========================================="
