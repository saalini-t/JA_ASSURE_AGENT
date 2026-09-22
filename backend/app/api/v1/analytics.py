from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.entities import Analytics
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

@router.get("/engagement")
def list_engagement_metrics(
    platform: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Real per-post engagement metrics, only ever written on a genuine successful
    LinkedIn API response (see POST /publishing/{id}/analytics/refresh) -- never
    fabricated. An empty list means no real engagement data has been fetched yet,
    not that engagement is zero.
    """
    query = select(Analytics)
    if platform:
        query = query.where(Analytics.platform == platform)
    if brand:
        query = query.where(Analytics.brand == brand)
    query = query.order_by(desc(Analytics.recorded_at)).limit(limit)
    rows = db.execute(query).scalars().all()
    return [
        {
            "id": r.id, "metric_name": r.metric_name, "brand": r.brand, "platform": r.platform,
            "metric_value": r.metric_value, "recorded_at": r.recorded_at,
        }
        for r in rows
    ]
