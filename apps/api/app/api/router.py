"""Versioned API router."""

from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.processing_jobs import router as processing_jobs_router
from app.api.routes.product_sources import router as product_sources_router
from app.api.routes.products import router as products_router
from app.api.routes.reviews import router as reviews_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(products_router)
api_router.include_router(product_sources_router)
api_router.include_router(processing_jobs_router)
api_router.include_router(reviews_router)
