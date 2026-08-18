"""Application factory and ASGI entry point."""

from fastapi import FastAPI

from backend.app.api.routes.admin import router as admin_router
from backend.app.api.routes.admin_audit import router as admin_audit_router
from backend.app.api.routes.admin_auth import router as admin_auth_router
from backend.app.api.routes.admin_conversations import (
    router as admin_conversations_router,
)
from backend.app.api.routes.admin_evaluation import (
    router as admin_evaluation_router,
)
from backend.app.api.routes.admin_users import router as admin_users_router
from backend.app.api.routes.admin_knowledge import router as admin_knowledge_router
from backend.app.api.routes.admin_widget import router as admin_widget_router
from backend.app.api.routes.customer_agents import router as customer_agents_router
from backend.app.api.routes.customer_conversations import router as customer_conversations_router
from backend.app.api.routes.customer_knowledge import router as customer_knowledge_router
from backend.app.api.routes.customer_widgets import router as customer_widgets_router
from backend.app.api.routes.chat import router as chat_router
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.knowledge import router as knowledge_router
from backend.app.api.routes.saas_onboarding import router as saas_onboarding_router
from backend.app.api.routes.tenant_auth import router as tenant_auth_router
from backend.app.api.routes.widget import router as widget_router
from backend.app.core.config import get_settings
from backend.app.core.widget_cors import WidgetCORSMiddleware


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )
    application.add_middleware(WidgetCORSMiddleware)
    application.include_router(health_router)
    application.include_router(admin_auth_router)
    application.include_router(tenant_auth_router)
    application.include_router(admin_router)
    application.include_router(admin_conversations_router)
    application.include_router(admin_evaluation_router)
    application.include_router(admin_users_router)
    application.include_router(admin_audit_router)
    application.include_router(admin_knowledge_router)
    application.include_router(admin_widget_router)
    application.include_router(customer_agents_router)
    application.include_router(customer_conversations_router)
    application.include_router(customer_knowledge_router)
    application.include_router(customer_widgets_router)
    application.include_router(widget_router)
    application.include_router(chat_router)
    application.include_router(knowledge_router)
    application.include_router(saas_onboarding_router)

    return application


app = create_app()
