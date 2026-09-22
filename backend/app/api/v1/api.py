from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.brands import router as brands_router
from app.api.v1.content import router as content_router
from app.api.v1.compliance import router as compliance_router
from app.api.v1.queue import router as queue_router
from app.api.v1.publishing import router as publishing_router
from app.api.v1.autonomous import router as autonomous_router
from app.api.v1.lessons import router as lessons_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.agents import router as agents_router
from app.api.v1.competitors import router as competitors_router
from app.api.v1.leads import router as leads_router
from app.api.v1.research import router as research_router

api_router = APIRouter()

# Core Active Pipeline Routers
api_router.include_router(health_router)
api_router.include_router(brands_router)
api_router.include_router(content_router)
api_router.include_router(compliance_router)
api_router.include_router(queue_router)
api_router.include_router(publishing_router)
api_router.include_router(autonomous_router)
api_router.include_router(lessons_router)
api_router.include_router(feedback_router)
api_router.include_router(analytics_router)
api_router.include_router(agents_router)

# Gated Modules
api_router.include_router(competitors_router)
api_router.include_router(leads_router)
api_router.include_router(research_router)
