from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import settings
from .api.routes import (
    colleges,
    courses,
    classes,
    subscriptions,
    auth,
    admin,
    notifications,
    stripe,
    user,
)
from .db.connection import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown"""
    # Startup
    print("🚀 Starting SeatSteal API...")
    init_db()
    print("✅ Database connection initialized")
    yield
    # Shutdown
    print("🛑 Shutting down SeatSteal API...")
    close_db()
    print("✅ Database connections closed")


# Create FastAPI application
app = FastAPI(
    title="SeatSteal API",
    version="1.0.0",
    description="Course enrollment tracking and notification system",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(colleges.router)
app.include_router(courses.router)
app.include_router(classes.router)
app.include_router(subscriptions.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(notifications.router)
app.include_router(stripe.router)
app.include_router(user.router)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "seatsteal-api",
        "version": "1.0.0",
        "environment": settings.PYTHON_ENV,
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to SeatSteal API",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=5000,
        reload=settings.PYTHON_ENV == "development",
    )
