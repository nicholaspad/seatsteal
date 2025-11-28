from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Any

from config import settings
from api.routes import (
    colleges,
    courses,
    classes,
    subscriptions,
    auth,
    admin,
    notifications,
    stripe,
    user,
    device_tokens,
)
from db.connection import init_db, close_db
from api.middleware.security_headers import SecurityHeadersMiddleware
from utils.cache import CacheClient


class PydanticJSONResponse(JSONResponse):
    """
    Custom JSON response class that serializes Pydantic models with by_alias=True
    to ensure camelCase field names in API responses.
    """

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        """Recursively serialize values, handling Pydantic models with by_alias=True"""
        if isinstance(value, BaseModel):
            return value.model_dump(by_alias=True, mode="json")
        elif isinstance(value, dict):
            return {
                k: PydanticJSONResponse._serialize_value(v) for k, v in value.items()
            }
        elif isinstance(value, (list, tuple)):
            return [PydanticJSONResponse._serialize_value(item) for item in value]
        return value

    def render(self, content: Any) -> bytes:
        """Override render to serialize Pydantic models with aliases"""
        serialized_content = self._serialize_value(content)
        return super().render(serialized_content)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown"""
    # Startup
    print("🚀 Starting SeatSteal API...")
    init_db()
    print("✅ Database connection initialized")

    # Initialize Redis connection
    redis_client = CacheClient.get_client()
    if redis_client:
        print("✅ Redis cache connection initialized")
    else:
        print("⚠️  Redis not configured, caching disabled")

    yield

    # Shutdown
    print("🛑 Shutting down SeatSteal API...")
    close_db()
    print("✅ Database connections closed")
    CacheClient.close()
    print("✅ Redis connection closed")


# Create FastAPI application
app = FastAPI(
    title="SeatSteal API",
    version="1.0.0",
    description="Course enrollment tracking and notification system",
    lifespan=lifespan,
    default_response_class=PydanticJSONResponse,
    # Disable documentation endpoints in production
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

# Security headers middleware (added first so it runs last)
app.add_middleware(SecurityHeadersMiddleware)

# GZip compression middleware for response compression (70-80% size reduction)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS middleware
# Allow both www and non-www variants in production, localhost in development
cors_origins = []

if settings.is_production:
    # In production, allow both www and non-www variants
    # This handles domain redirects and direct access from either variant
    cors_origins.extend(
        [
            "https://seatsteal.app",
            "https://www.seatsteal.app",
        ]
    )
else:
    # In development, allow localhost and the configured frontend URL
    cors_origins.extend(
        [
            settings.FRONTEND_URL,
            "http://localhost:5173",
            "http://localhost:3000",
        ]
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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
app.include_router(device_tokens.router)


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
    """Root endpoint - disabled in production"""
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Not found")
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
