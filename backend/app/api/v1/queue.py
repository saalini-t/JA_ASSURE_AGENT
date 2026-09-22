import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from app.database.session import get_db
from app.models.entities import ContentQueue, Feedback, ReviewDecision
from app.schemas.dtos import (
    ContentQueueCreate,
    ContentQueueUpdate,
    ContentQueueResponse,
    ReviewDecisionResponse,
)
from app.services.compliance_service import compliance_service
from app.services.lessons_service import lessons_service
from app.services.content_service import content_service
from app.schemas.agent_contracts import ContentBrief
from app.services import hitl_service
from app.services.hitl_service import HITLTransitionError

router = APIRouter(prefix="/queue", tags=["Content Queue & Human Review"])

# Statuses that must never be assignable at creation time via the public API.
# Publish-readiness may only be reached by walking the HITL state machine
# (see app.services.hitl_service), never by fabricating a row directly.
_PRIVILEGED_STATUSES = {"approved", "scheduled", "published"}

class RejectRequest(BaseModel):
    reason_tag: str
    notes: str
    reviewer: Optional[str] = "compliance_officer"

class EditRequest(BaseModel):
    edited_content: str
    reason_tag: Optional[str] = "human_edit"
    notes: Optional[str] = "Edited during human review"
    reviewer: Optional[str] = "compliance_officer"

@router.get("", response_model=List[ContentQueueResponse])
def list_queue(
    brand: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    compliance_status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = select(ContentQueue)
    if brand:
        query = query.where(ContentQueue.brand == brand.lower())
    if platform:
        query = query.where(ContentQueue.platform == platform.lower())
    if status:
        query = query.where(ContentQueue.status == status)
    if compliance_status:
        query = query.where(ContentQueue.compliance_status == compliance_status)

    query = query.order_by(desc(ContentQueue.created_at)).offset(offset).limit(limit)
    return db.execute(query).scalars().all()

@router.get("/pending", response_model=List[ContentQueueResponse])
def get_pending_content(db: Session = Depends(get_db)):
    """Retrieve content items awaiting human review."""
    query = select(ContentQueue).where(ContentQueue.status.in_(["human_review", "pending"])).order_by(desc(ContentQueue.created_at))
    return db.execute(query).scalars().all()

@router.get("/approved", response_model=List[ContentQueueResponse])
def get_approved_content(db: Session = Depends(get_db)):
    """Retrieve content items that have received human sign-off."""
    query = select(ContentQueue).where(ContentQueue.status.in_(["approved", "scheduled", "published"])).order_by(desc(ContentQueue.created_at))
    return db.execute(query).scalars().all()

@router.get("/rejected", response_model=List[ContentQueueResponse])
def get_rejected_content(db: Session = Depends(get_db)):
    """Retrieve rejected items with feedback tags."""
    query = select(ContentQueue).where(ContentQueue.status == "rejected").order_by(desc(ContentQueue.created_at))
    return db.execute(query).scalars().all()

@router.get("/{item_id}", response_model=ContentQueueResponse)
def get_queue_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(ContentQueue, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Content item {item_id} not found")
    return item

@router.get("/{item_id}/history", response_model=List[ReviewDecisionResponse])
def get_review_history(item_id: int, db: Session = Depends(get_db)):
    """
    Full HITL audit trail for a content item: every approve/reject/edit/rewrite/regenerate
    decision, who made it, what changed, and the status transition it caused.
    """
    item = db.get(ContentQueue, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Content item {item_id} not found")
    query = (
        select(ReviewDecision)
        .where(ReviewDecision.asset_type == "content_queue", ReviewDecision.asset_id == item_id)
        .order_by(ReviewDecision.created_at)
    )
    return db.execute(query).scalars().all()

@router.post("/{item_id}/approve", response_model=ContentQueueResponse)
def approve_content(
    item_id: int,
    notes: Optional[str] = None,
    reviewer: Optional[str] = Query("compliance_officer"),
    db: Session = Depends(get_db)
):
    """
    Mandatory human approval action.
    Only legal from a HUMAN_REVIEW status (see hitl_service). Advances content item to
    'approved', which is a NECESSARY but not SUFFICIENT condition to publish — the
    publishing gate independently requires compliance_status == 'passed' as well.
    """
    item = db.get(ContentQueue, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Content item not found")

    previous_status = item.status
    try:
        new_status = hitl_service.assert_transition_allowed(previous_status, "approve")
    except HITLTransitionError as e:
        raise HTTPException(status_code=409, detail=e.message)

    item.status = new_status
    if notes:
        item.notes = notes

    hitl_service.record_decision(
        db,
        asset_id=item.id,
        decision="approve",
        previous_status=previous_status,
        new_status=new_status,
        reviewer=reviewer,
        notes=notes,
        compliance_score=item.compliance_score,
    )

    db.commit()
    db.refresh(item)
    return item

@router.post("/{item_id}/reject", response_model=ContentQueueResponse)
def reject_content(item_id: int, req: RejectRequest, db: Session = Depends(get_db)):
    """
    Human rejection action.
    Only legal from a HUMAN_REVIEW status. Marks item as 'rejected' and synthesizes/updates
    an active Lesson Learned in the DB (existing closed-loop behavior, unchanged).
    """
    item = db.get(ContentQueue, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Content item not found")

    previous_status = item.status
    try:
        new_status = hitl_service.assert_transition_allowed(previous_status, "reject")
    except HITLTransitionError as e:
        raise HTTPException(status_code=409, detail=e.message)

    item.status = new_status
    item.reason_tag = req.reason_tag
    item.notes = req.notes

    # Ingest into closed-loop learning system (unchanged existing behavior)
    lessons_service.record_feedback_and_synthesize(
        content_id=item.id,
        reason_tag=req.reason_tag,
        notes=req.notes,
        original_content=item.content_raw
    )

    hitl_service.record_decision(
        db,
        asset_id=item.id,
        decision="reject",
        previous_status=previous_status,
        new_status=new_status,
        reviewer=req.reviewer,
        reason_tag=req.reason_tag,
        notes=req.notes,
        original_content=item.content_raw,
        compliance_score=item.compliance_score,
    )

    db.commit()
    db.refresh(item)
    return item

@router.post("/{item_id}/edit", response_model=ContentQueueResponse)
async def edit_content(item_id: int, req: EditRequest, db: Session = Depends(get_db)):
    """
    Human edit action.
    Only legal from a HUMAN_REVIEW status. Preserves the original AI-generated text
    (original_content_raw is set once and never overwritten), re-runs the compliance gate
    against the EDITED text (stale pre-edit compliance results must not carry over), and
    returns the item to 'human_review' — an edit is a NEW version that itself requires a
    fresh human sign-off, it is never auto-approved.
    """
    item = db.get(ContentQueue, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Content item not found")

    previous_status = item.status
    try:
        new_status = hitl_service.assert_transition_allowed(previous_status, "edit")
    except HITLTransitionError as e:
        raise HTTPException(status_code=409, detail=e.message)

    original_text = item.content_raw
    if item.original_content_raw is None:
        item.original_content_raw = original_text

    item.content_raw = req.edited_content
    item.reason_tag = req.reason_tag or "human_edit"
    item.notes = req.notes or "Edited during human review"

    # Re-evaluate compliance against the edited text; a compliance status computed against
    # the pre-edit text is no longer trustworthy once the wording has changed.
    comp = await compliance_service.evaluate_content(
        brand=item.brand,
        content_text=req.edited_content,
        content_type=item.content_type
    )
    item.compliance_status = "passed" if comp.passed else "flagged"
    item.compliance_score = comp.score

    item.status = new_status  # always back to 'human_review' — never auto-approved

    # Record feedback (existing closed-loop behavior, unchanged)
    lessons_service.record_feedback_and_synthesize(
        content_id=item.id,
        reason_tag=item.reason_tag,
        notes=item.notes,
        original_content=original_text,
        corrected_content=req.edited_content
    )

    hitl_service.record_decision(
        db,
        asset_id=item.id,
        decision="edit",
        previous_status=previous_status,
        new_status=new_status,
        reviewer=req.reviewer,
        reason_tag=item.reason_tag,
        notes=item.notes,
        original_content=original_text,
        edited_content=req.edited_content,
        compliance_score=comp.score,
    )

    db.commit()
    db.refresh(item)
    return item

@router.post("/{item_id}/compliance", response_model=ContentQueueResponse)
async def rerun_compliance(item_id: int, db: Session = Depends(get_db)):
    """
    Re-evaluate compliance gate on current content text.
    """
    item = db.get(ContentQueue, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Content item not found")

    res = await compliance_service.evaluate_content(
        brand=item.brand,
        content_text=item.content_raw,
        content_type=item.content_type
    )

    item.compliance_status = "passed" if res.passed else "flagged"
    item.compliance_score = res.score
    item.notes = res.overall_feedback
    if res.violations:
        item.reason_tag = res.violations[0].rule_id

    # Enrich metadata_json with audit trail and violation breakdown
    try:
        current_meta = json.loads(item.metadata_json) if item.metadata_json else {}
    except Exception:
        current_meta = {}
    current_meta["compliance_status"] = res.status
    current_meta["compliance_score"] = res.score
    current_meta["compliance_jurisdiction"] = res.jurisdiction
    current_meta["compliance_product"] = res.product
    current_meta["compliance_disclaimer_status"] = res.disclaimer_status
    current_meta["compliance_violations"] = [
        v.model_dump() if hasattr(v, "model_dump") else v for v in res.violations
    ]
    current_meta["compliance_warnings"] = [
        w.model_dump() if hasattr(w, "model_dump") else w for w in res.warnings
    ]
    current_meta["claims_analyzed"] = [
        c.model_dump() if hasattr(c, "model_dump") else c for c in res.claims_analyzed
    ]
    item.metadata_json = json.dumps(current_meta)

    db.commit()
    db.refresh(item)
    return item

@router.post("/{item_id}/regenerate", response_model=ContentQueueResponse)
async def regenerate_content(item_id: int, db: Session = Depends(get_db)):
    """
    Regenerate content item using updated active lessons learned from human feedback.
    Legal from a HUMAN_REVIEW status or from 'rejected' (closed-loop re-draft after rejection).
    """
    item = db.get(ContentQueue, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Content item not found")

    previous_status = item.status
    try:
        new_status = hitl_service.assert_transition_allowed(previous_status, "regenerate")
    except HITLTransitionError as e:
        raise HTTPException(status_code=409, detail=e.message)

    active_lessons = lessons_service.get_relevant_lessons_for_prompt(brand=item.brand, platform=item.platform)
    brief = ContentBrief(
        brand=item.brand,
        platform=item.platform,
        content_type=item.content_type,
        topic=item.topic,
        language=item.language,
        variations_count=1,
        context_lessons=active_lessons
    )

    original_text = item.content_raw
    variations = await content_service.generate_variations(brief)
    if variations:
        new_var = variations[0]
        if item.original_content_raw is None:
            item.original_content_raw = original_text
        item.content_raw = new_var.content_text
        item.status = new_status # pending review again
        # re-evaluate compliance
        comp = await compliance_service.evaluate_content(
            brand=item.brand,
            content_text=new_var.content_text,
            content_type=item.content_type
        )
        item.compliance_status = "passed" if comp.passed else "flagged"
        item.compliance_score = comp.score
        item.notes = f"Regenerated with {len(active_lessons)} active lessons learned. Compliance: {comp.overall_feedback}"
        try:
            current_meta = json.loads(item.metadata_json) if item.metadata_json else {}
        except Exception:
            current_meta = {}
        current_meta["compliance_status"] = comp.status
        current_meta["compliance_score"] = comp.score
        current_meta["compliance_jurisdiction"] = comp.jurisdiction
        current_meta["compliance_violations"] = [
            v.model_dump() if hasattr(v, "model_dump") else v for v in comp.violations
        ]
        item.metadata_json = json.dumps(current_meta)

        hitl_service.record_decision(
            db,
            asset_id=item.id,
            decision="regenerate",
            previous_status=previous_status,
            new_status=new_status,
            reviewer="ai_regeneration_agent",
            notes=item.notes,
            original_content=original_text,
            edited_content=new_var.content_text,
            compliance_score=comp.score,
        )

    db.commit()
    db.refresh(item)
    return item

@router.post("/{item_id}/rewrite", response_model=ContentQueueResponse)
async def rewrite_queue_item(item_id: int, db: Session = Depends(get_db)):
    """
    Automated Compliance Rewrite workflow:
    Rewrites non-compliant copy, re-checks compliance score, and places
    item into 'human_review' status for human verification.
    Legal only from a HUMAN_REVIEW status — a rejected/approved/scheduled item must not
    be silently rewritten out from under whatever decision was already made about it.
    """
    item = db.get(ContentQueue, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Content item not found")

    previous_status = item.status
    try:
        new_status = hitl_service.assert_transition_allowed(previous_status, "rewrite")
    except HITLTransitionError as e:
        raise HTTPException(status_code=409, detail=e.message)

    original_text = item.content_raw
    if item.original_content_raw is None:
        item.original_content_raw = original_text

    rewrite_res = await compliance_service.rewrite_non_compliant_content(
        brand=item.brand,
        original_text=original_text
    )

    item.content_raw = rewrite_res["corrected_text"]
    item.compliance_score = rewrite_res["new_score"]
    item.compliance_status = "passed" if rewrite_res["new_passed"] else "flagged"
    item.status = new_status # MANDATORY: never auto-approved
    item.notes = f"Compliance rewrite completed. Score improved from {rewrite_res['previous_score']} to {rewrite_res['new_score']}. Awaiting human review."

    hitl_service.record_decision(
        db,
        asset_id=item.id,
        decision="rewrite",
        previous_status=previous_status,
        new_status=new_status,
        reviewer="ai_compliance_rewrite",
        notes=item.notes,
        original_content=original_text,
        edited_content=rewrite_res["corrected_text"],
        compliance_score=rewrite_res["new_score"],
    )

    db.commit()
    db.refresh(item)
    return item

@router.post("", response_model=ContentQueueResponse, status_code=201)
def create_queue_item(item_in: ContentQueueCreate, db: Session = Depends(get_db)):
    """
    Direct row creation (used by tests/manual seeding; the real generation path is
    pipeline_service, which never sets status to a privileged value). Server-side clamp:
    a caller cannot fabricate an 'approved'/'scheduled'/'published' asset out of thin air —
    any such request is forced back to 'pending' so it must still pass through human review.
    """
    payload = item_in.model_dump()
    if payload.get("status") in _PRIVILEGED_STATUSES:
        payload["status"] = "pending"
    if payload.get("original_content_raw") is None:
        payload["original_content_raw"] = payload.get("content_raw")
    item = ContentQueue(**payload)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@router.patch("/{item_id}", response_model=ContentQueueResponse)
def update_queue_item(item_id: int, item_in: ContentQueueUpdate, db: Session = Depends(get_db)):
    item = db.get(ContentQueue, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Content item {item_id} not found")

    update_data = item_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return item

@router.delete("/{item_id}", status_code=204)
def delete_queue_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(ContentQueue, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Content item {item_id} not found")
    db.delete(item)
    db.commit()
    return None
