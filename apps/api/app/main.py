"""FastAPI application factory and default application instance."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.core.request_context import RequestIdMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the API with validated deployment-aware settings."""
    resolved = settings or get_settings()
    configure_logging(resolved.log_level)
    application = FastAPI(
        title=resolved.app_name,
        debug=resolved.app_debug,
        version="0.1.0",
        docs_url="/docs" if resolved.app_env != "production" else None,
        redoc_url=None,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Accept", "Content-Type"],
    )
    application.add_middleware(RequestIdMiddleware)
    register_exception_handlers(application)
    application.include_router(api_router)
    return application


app = create_app()
