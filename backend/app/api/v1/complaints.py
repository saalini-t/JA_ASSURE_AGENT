"""
Complaints REST API endpoints (v1) - Abhi Ram's contribution.
Provides endpoints for capturing complaints, querying/filtering,
automated and manual department routing, and resolution workflows.
Strictly segregated from the marketing content pipeline.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.dtos import (
    ComplaintCreate,
    ComplaintResponse,
    ComplaintRouteRequest,
    ComplaintActionRequest,
    ComplaintStatusUpdate,
    ComplaintMetricsResponse,
)
from app.services.complaints_service import complaints_service

router = APIRouter(prefix="/complaints", tags=["Complaints Handling"])


@router.post("/", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
def submit_complaint(
    complaint_in: ComplaintCreate,
    db: Session = Depends(get_db)
):
    """
    Submit a customer/policyholder complaint.
    Stores the record in SQLite with a unique CMP tracking ID and auto-classifies
    the destination department and priority.
    """
    try:
        complaint = complaints_service.submit_complaint(db, complaint_in)
        return complaint
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit complaint: {str(e)}"
        )


@router.get("/", response_model=List[ComplaintResponse])
def list_complaints(
    brand: Optional[str] = Query(None, description="Filter by brand (jade, doctorshield, jaguartransit)"),
    status: Optional[str] = Query(None, description="Filter by status (pending, routed, under_review, actioned, resolved, rejected)"),
    priority: Optional[str] = Query(None, description="Filter by priority (low, medium, high, urgent)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    routed_to: Optional[str] = Query(None, description="Filter by assigned department"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Query complaints from SQLite with multi-factor filtering and pagination.
    """
    return complaints_service.get_complaints(
        db,
        brand=brand,
        status=status,
        priority=priority,
        category=category,
        routed_to=routed_to,
        limit=limit,
        offset=offset
    )


@router.get("/metrics", response_model=ComplaintMetricsResponse)
def get_complaint_metrics(db: Session = Depends(get_db)):
    """
    Get complaint metrics: volume by status, brand, category, priority, and department.
    """
    return complaints_service.get_metrics(db)


@router.get("/{complaint_id}", response_model=ComplaintResponse)
def get_complaint(
    complaint_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve single complaint details by ID.
    """
    complaint = complaints_service.get_complaint_by_id(db, complaint_id)
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with ID {complaint_id} not found."
        )
    return complaint


@router.post("/{complaint_id}/route", response_model=ComplaintResponse)
def route_complaint(
    complaint_id: int,
    route_req: ComplaintRouteRequest,
    db: Session = Depends(get_db)
):
    """
    Route complaint to a specialized department (claims_desk, underwriting_team, compliance_legal, etc.)
    and optionally assign a reviewer.
    """
    complaint = complaints_service.route_complaint(db, complaint_id, route_req)
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with ID {complaint_id} not found."
        )
    return complaint


@router.post("/{complaint_id}/action", response_model=ComplaintResponse)
def action_complaint(
    complaint_id: int,
    action_req: ComplaintActionRequest,
    db: Session = Depends(get_db)
):
    """
    Action or resolve a complaint with resolution notes, draft response, and audit user.
    """
    complaint = complaints_service.action_complaint(db, complaint_id, action_req)
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with ID {complaint_id} not found."
        )
    return complaint


@router.patch("/{complaint_id}/status", response_model=ComplaintResponse)
def update_complaint_status(
    complaint_id: int,
    status_update: ComplaintStatusUpdate,
    db: Session = Depends(get_db)
):
    """
    Transition complaint status (pending -> under_review -> routed -> actioned -> resolved/rejected).
    """
    complaint = complaints_service.update_status(db, complaint_id, status_update)
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with ID {complaint_id} not found."
        )
    return complaint
