from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from app.database.session import get_db
from app.models.entities import PublishingRecord, ContentQueue
from app.schemas.dtos import PublishingRecordCreate, PublishingRecordResponse
from app.services.hitl_service import is_publishable
from app.services import publishing_service
from app.services.publishing_service import PublishingGateError, DuplicatePublishError
from app.services.analytics_service import analytics_service
from app.services import publishing_worker

router = APIRouter(prefix="/publishing", tags=["Publishing"])

@router.get("", response_model=List[PublishingRecordResponse])
def list_publishing_records(db: Session = Depends(get_db)):
    """
    List all simulated publishing dispatch records ordered by most recent.
    """
    query = select(PublishingRecord).order_by(desc(PublishingRecord.created_at))
    return db.execute(query).scalars().all()

@router.get("/{record_id}", response_model=PublishingRecordResponse)
def get_publishing_record(record_id: int, db: Session = Depends(get_db)):
    """
    Retrieve details of a specific simulated dispatch record.
    """
    record = db.get(PublishingRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Publishing record not found")
    return record

@router.post("", response_model=PublishingRecordResponse, status_code=201)
def schedule_publishing(item_in: PublishingRecordCreate, db: Session = Depends(get_db)):
    """
    Human-controlled publishing dispatch preview.
    STRICT GOVERNANCE RULES (single source of truth: app.services.hitl_service.is_publishable):
    1. Only human-approved (status == 'approved') content can reach simulated dispatch.
    2. AND compliance_status must be exactly 'passed' — pending, human_review, rejected,
       and compliance-flagged/failed content are all rejected, regardless of score.
    3. Persists dispatch record in SQLite/Postgres with status 'scheduled'.
    """
    content = db.get(ContentQueue, item_in.content_id)
    if not content:
        raise HTTPException(status_code=404, detail=f"Content item #{item_in.content_id} not found")

    if not is_publishable(content.status, content.compliance_status):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot schedule content unless status='approved' AND compliance_status='passed'. "
                f"Only human-approved content can reach publishing dispatch. "
                f"Current: status='{content.status}', compliance_status='{content.compliance_status}' "
                f"(score={content.compliance_score})."
            )
        )

    # Create dispatch record
    record = PublishingRecord(
        content_id=item_in.content_id,
        platform=item_in.platform or content.platform,
        status="scheduled",
        scheduled_at=item_in.scheduled_at or datetime.now(timezone.utc),
        engagement_metrics="{\"dispatch_mode\": \"simulated_preview\", \"external_api\": \"none\"}",
        created_at=datetime.now(timezone.utc)
    )
    db.add(record)

    # Update content queue item status
    content.status = "scheduled"
    
    db.commit()
    db.refresh(record)
    return record

@router.post("/{content_id}/linkedin", response_model=PublishingRecordResponse)
async def publish_content_to_linkedin(content_id: int, db: Session = Depends(get_db)):
    """
    Dispatch one ContentQueue item to LinkedIn for real.
    STRICT GOVERNANCE (identical gate to POST /publishing, single source of truth:
    app.services.hitl_service.is_publishable): only status='approved' AND
    compliance_status='passed' may reach LinkedIn. The LinkedIn client itself is never
    reachable from a route -- publishing_service.publish_to_linkedin() is the only caller.

    Idempotent: if this content item already has a successful LinkedIn PublishingRecord,
    returns 409 rather than posting a duplicate. Transient failures (timeout, network,
    5xx, rate limiting) are retried with bounded backoff; permanent failures (missing
    token, invalid payload, invalid asset, auth failure) are not retried. Every attempt
    is persisted as its own immutable PublishingRecord row.
    """
    try:
        record = await publishing_service.publish_to_linkedin(db, content_id)
        return record
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PublishingGateError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except DuplicatePublishError as e:
        raise HTTPException(status_code=409, detail=e.message)


@router.patch("/{record_id}/cancel", response_model=PublishingRecordResponse)
def cancel_scheduled_publishing(record_id: int, db: Session = Depends(get_db)):
    """
    Cancel a scheduled dispatch and revert the content item status to 'approved'.
    """
    record = db.get(PublishingRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Publishing record not found")
    
    record.status = "cancelled"
    
    content = db.get(ContentQueue, record.content_id)
    if content and content.status == "scheduled":
        content.status = "approved"

    db.commit()
    db.refresh(record)
    return record


@router.post("/{record_id}/analytics/refresh", response_model=PublishingRecordResponse)
async def refresh_publishing_record_analytics(record_id: int):
    """
    Attempts a REAL LinkedIn engagement fetch (likes/comments) for this published
    record. Never fabricates numbers -- if the configured token lacks read scope
    (the common case for a publish-only token) or the request otherwise fails,
    engagement_metrics is set to an honest {"source": "unavailable", "reason": ...}
    payload, never invented numbers presented as real.
    """
    try:
        record = await analytics_service.refresh_linkedin_engagement(record_id)
        return record
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/worker/run-once")
async def run_publishing_worker_once(max_items: int = Query(10, ge=1, le=50)):
    """
    Project 2 ("The Hands") -- runs exactly ONE polling pass of the publishing
    worker: finds approved + compliance-passed content not yet published to
    LinkedIn, and publishes each through the exact same gated
    publishing_service.publish_to_linkedin() every other publish path uses.

    Deliberately manual/on-demand only -- this is NOT scheduled automatically.
    Every call is one explicit, human-triggered batch, matching this codebase's
    standing rule that publishing a real post always requires an explicit action.
    """
    results = await publishing_worker.run_once(max_items=max_items)
    return {"processed": len(results), "results": results}
