"""Application factory and ASGI entry point."""

from fastapi import FastAPI

from backend.app.api.routes.chat import router as chat_router
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.handoffs import router as handoff_router
from backend.app.api.routes.knowledge import router as knowledge_router
from backend.app.core.config import get_settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )
    application.include_router(health_router)
    application.include_router(chat_router)
    application.include_router(knowledge_router)
    application.include_router(handoff_router)

    return application


app = create_app()
