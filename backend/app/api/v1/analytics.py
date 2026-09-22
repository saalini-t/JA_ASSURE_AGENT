from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.dtos import DashboardSummary
from app.services.analytics_service import analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics & Closed-Loop Metrics"])

@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary():
    """
    Returns comprehensive analytics, rejection rates, compliance scores,
    and feedback reason frequencies proving closed-loop learning.
    """
    return analytics_service.get_summary()
