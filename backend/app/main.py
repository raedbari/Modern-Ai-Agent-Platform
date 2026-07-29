"""Application factory and ASGI entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.app.api.routes.chat import router as chat_router
from backend.app.api.routes.health import router as health_router
from backend.app.core.config import get_settings
from backend.app.core.errors import (
    BusinessError,
    business_error_handler,
    generic_exception_handler,
    http_exception_handler,
)
from backend.app.core.rate_limit import limiter
from backend.app.db.base import Base, engine
from fastapi import HTTPException


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    # Create database tables
    Base.metadata.create_all(bind=engine)

    # Configure CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # Add rate limiter
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Add error handlers
    application.add_exception_handler(BusinessError, business_error_handler)
    application.add_exception_handler(HTTPException, http_exception_handler)
    application.add_exception_handler(Exception, generic_exception_handler)

    # Include routers
    application.include_router(health_router)
    application.include_router(chat_router)

    return application


app = create_app()
