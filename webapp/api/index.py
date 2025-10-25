"""
Vercel serverless function entry point for SeatSteal API.

This module serves as the entry point for Vercel's Python runtime,
importing and exposing the FastAPI application for serverless deployment.

Note: The application uses database connection pooling with pool_pre_ping=True
to handle serverless cold starts and connection management.
"""

from app import app

# Export the FastAPI app instance for Vercel
__all__ = ["app"]
