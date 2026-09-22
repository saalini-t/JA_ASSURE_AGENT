from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.database.session import get_db
from app.models.entities import PublishingRecord, ContentQueue
from app.schemas.dtos import PublishingRecordCreate, PublishingRecordResponse
from app.services.hitl_service import is_publishable
from app.services.publishing.linkedin_publisher import linkedin_publisher, LinkedInPublishResult

router = APIRouter(prefix="/publishing", tags=["Publishing"])

class LivePublishRequest(BaseModel):
    item_id: Optional[int] = None
    text: str
    media_path: Optional[str] = None
    media_type: Optional[str] = None
    title: Optional[str] = None
    dry_run: bool = False

@router.get("", response_model=List[PublishingRecordResponse])
def list_publishing_records(db: Session = Depends(get_db)):
    query = select(PublishingRecord).order_by(desc(PublishingRecord.created_at))
    return db.execute(query).scalars().all()

@router.get("/{record_id}", response_model=PublishingRecordResponse)
def get_publishing_record(record_id: int, db: Session = Depends(get_db)):
    record = db.get(PublishingRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Publishing record not found")
    return record

@router.post("/linkedin/dispatch")
def dispatch_to_linkedin(req: LivePublishRequest, db: Session = Depends(get_db)):
    """
    Directly dispatches real media & copy to LinkedIn using official REST endpoints.
    """
    res: LinkedInPublishResult = linkedin_publisher.publish_content(
        text=req.text,
        media_path=req.media_path,
        media_type=req.media_type,
        title=req.title,
        dry_run=req.dry_run
    )

    if req.item_id:
        content = db.get(ContentQueue, req.item_id)
        if content:
            if res.success:
                content.status = "published"
                pub_record = PublishingRecord(
                    content_id=content.id,
                    platform="linkedin",
                    external_post_id=res.post_id,
                    status="published",
                    scheduled_at=datetime.now(timezone.utc),
                    published_at=datetime.now(timezone.utc),
                    engagement_metrics=str(res.direct_url),
                    error_info=None
                )
                db.add(pub_record)
                db.commit()

    return res

@router.post("", response_model=PublishingRecordResponse, status_code=201)
def schedule_publishing(item_in: PublishingRecordCreate, db: Session = Depends(get_db)):
    content = db.get(ContentQueue, item_in.content_id)
    if not content:
        raise HTTPException(status_code=404, detail=f"Content item #{item_in.content_id} not found")

    if not is_publishable(content.status, content.compliance_status):
        raise HTTPException(
            status_code=400,
            detail=f"Only human-approved content can reach publishing dispatch. Cannot schedule content unless status='approved' AND compliance_status='passed'. Current: status='{content.status}', compliance_status='{content.compliance_status}'"
        )

    record = PublishingRecord(
        content_id=item_in.content_id,
        platform=item_in.platform or content.platform,
        status="scheduled",
        scheduled_at=item_in.scheduled_at or datetime.now(timezone.utc),
        engagement_metrics="{\"dispatch_mode\": \"scheduled\"}",
        created_at=datetime.now(timezone.utc)
    )
    db.add(record)
    content.status = "scheduled"
    db.commit()
    db.refresh(record)
    return record

@router.patch("/{record_id}/cancel", response_model=PublishingRecordResponse)
def cancel_scheduled_publishing(record_id: int, db: Session = Depends(get_db)):
    record = db.get(PublishingRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Publishing record not found")
    record.status = "cancelled"
    
    # Revert queue item to approved
    content = db.get(ContentQueue, record.content_id)
    if content and content.status == "scheduled":
        content.status = "approved"
    
    db.commit()
    db.refresh(record)
    return record

