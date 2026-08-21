"""Versioned API router."""

from fastapi import APIRouter

from app.api.routes.catalog import router as catalog_router
from app.api.routes.catalog_search import router as catalog_search_router
from app.api.routes.catalog_workflows import router as catalog_workflows_router
from app.api.routes.health import router as health_router
from app.api.routes.processing_jobs import router as processing_jobs_router
from app.api.routes.product_intelligence import router as product_intelligence_router
from app.api.routes.product_sources import router as product_sources_router
from app.api.routes.products import router as products_router
from app.api.routes.reviews import router as reviews_router
from app.api.routes.unilog_evaluation import router as unilog_evaluation_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(products_router)
api_router.include_router(catalog_router)
api_router.include_router(catalog_search_router)
api_router.include_router(catalog_workflows_router)
api_router.include_router(product_intelligence_router)
api_router.include_router(product_sources_router)
api_router.include_router(processing_jobs_router)
api_router.include_router(reviews_router)
api_router.include_router(unilog_evaluation_router)
