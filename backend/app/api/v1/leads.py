import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from app.database.session import get_db
from app.models.entities import Lead, LeadOutreach
from app.schemas.dtos import LeadCreate, LeadResponse, LeadOutreachResponse
from app.schemas.agent_contracts import LeadProspect
from app.services.lead_service import lead_service
from app.services.compliance_service import compliance_service
from app.services import hitl_service
from app.services.hitl_service import HITLTransitionError
from app.services.email_provider import get_email_provider, EmailSendError

router = APIRouter(prefix="/leads", tags=["Lead Generation & Scoring"])


class RejectOutreachRequest(BaseModel):
    reason_tag: str
    notes: str
    reviewer: Optional[str] = "compliance_officer"


class EditOutreachRequest(BaseModel):
    edited_body: str
    edited_subject: Optional[str] = None
    reason_tag: Optional[str] = "human_edit"
    notes: Optional[str] = "Edited during human review"
    reviewer: Optional[str] = "compliance_officer"

class DiscoverLeadsRequest(BaseModel):
    brand: Optional[str] = None
    country: Optional[str] = None
    industry: Optional[str] = None
    target_audience: Optional[str] = None
    keywords: Optional[str] = None

class EnrichLeadRequest(BaseModel):
    source_url: Optional[str] = None

@router.get("", response_model=List[LeadResponse])
def list_leads(
    industry: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    query = select(Lead)
    if industry:
        query = query.where(Lead.industry.ilike(f"%{industry}%"))
    if status:
        query = query.where(Lead.status == status)
    if min_score is not None:
        query = query.where(Lead.fit_score >= min_score)
    query = query.order_by(desc(Lead.fit_score)).limit(limit)
    return db.execute(query).scalars().all()

@router.post("/discover", response_model=List[LeadProspect])
async def discover_and_score_leads(req: DiscoverLeadsRequest):
    """
    Run the lead agent discovery & scoring pipeline.
    Uses Gemini AI prospect discovery when live or curated demo pool offline.
    Scores candidates with the 5-factor model, generates contextual outreach,
    and stores prospects in SQLite.
    """
    try:
        prospects = await lead_service.discover_and_score_leads(
            brand=req.brand,
            country=req.country,
            industry=req.industry,
            target_audience=req.target_audience,
            keywords=req.keywords
        )
        return prospects
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lead discovery failed: {str(e)}")

@router.get("/outreach/{outreach_id}", response_model=LeadOutreachResponse)
def get_lead_outreach(outreach_id: int, db: Session = Depends(get_db)):
    outreach = db.get(LeadOutreach, outreach_id)
    if not outreach:
        raise HTTPException(status_code=404, detail="Outreach draft not found")
    return LeadOutreachResponse.from_orm_with_json(outreach)

@router.post("/outreach/{outreach_id}/approve", response_model=LeadOutreachResponse)
def approve_lead_outreach(
    outreach_id: int, reviewer: Optional[str] = Query("compliance_officer"), db: Session = Depends(get_db)
):
    """
    Mandatory human approval action for an outreach draft. Only legal from
    'human_review' (see hitl_service) -- the SAME governance primitives that guard
    ContentQueue guard this. Never automatically approved; email sending is not
    implemented in this phase regardless of approval status (draft-only, per spec).
    """
    outreach = db.get(LeadOutreach, outreach_id)
    if not outreach:
        raise HTTPException(status_code=404, detail="Outreach draft not found")

    previous_status = outreach.status
    try:
        new_status = hitl_service.assert_transition_allowed(previous_status, "approve")
    except HITLTransitionError as e:
        raise HTTPException(status_code=409, detail=e.message)

    outreach.status = new_status
    hitl_service.record_decision(
        db, asset_id=outreach.id, asset_type="lead_outreach", decision="approve",
        previous_status=previous_status, new_status=new_status, reviewer=reviewer,
        compliance_score=outreach.compliance_score,
    )
    db.commit()
    db.refresh(outreach)
    return LeadOutreachResponse.from_orm_with_json(outreach)

@router.post("/outreach/{outreach_id}/reject", response_model=LeadOutreachResponse)
def reject_lead_outreach(outreach_id: int, req: RejectOutreachRequest, db: Session = Depends(get_db)):
    outreach = db.get(LeadOutreach, outreach_id)
    if not outreach:
        raise HTTPException(status_code=404, detail="Outreach draft not found")

    previous_status = outreach.status
    try:
        new_status = hitl_service.assert_transition_allowed(previous_status, "reject")
    except HITLTransitionError as e:
        raise HTTPException(status_code=409, detail=e.message)

    outreach.status = new_status
    outreach.reason_tag = req.reason_tag
    outreach.notes = req.notes

    hitl_service.record_decision(
        db, asset_id=outreach.id, asset_type="lead_outreach", decision="reject",
        previous_status=previous_status, new_status=new_status, reviewer=req.reviewer,
        reason_tag=req.reason_tag, notes=req.notes, original_content=outreach.body,
        compliance_score=outreach.compliance_score,
    )
    db.commit()
    db.refresh(outreach)
    return LeadOutreachResponse.from_orm_with_json(outreach)

@router.post("/outreach/{outreach_id}/edit", response_model=LeadOutreachResponse)
async def edit_lead_outreach(outreach_id: int, req: EditOutreachRequest, db: Session = Depends(get_db)):
    """
    Human edit action. Re-runs compliance against the EDITED body (a compliance
    result computed against the pre-edit text is stale once wording changes) and
    always returns to 'human_review' -- an edit is never auto-approved.
    """
    outreach = db.get(LeadOutreach, outreach_id)
    if not outreach:
        raise HTTPException(status_code=404, detail="Outreach draft not found")

    previous_status = outreach.status
    try:
        new_status = hitl_service.assert_transition_allowed(previous_status, "edit")
    except HITLTransitionError as e:
        raise HTTPException(status_code=409, detail=e.message)

    original_body = outreach.body
    if outreach.original_body is None:
        outreach.original_body = original_body

    outreach.body = req.edited_body
    if req.edited_subject:
        outreach.subject = req.edited_subject
    outreach.reason_tag = req.reason_tag or "human_edit"
    outreach.notes = req.notes or "Edited during human review"

    comp = await compliance_service.evaluate_content(
        brand=outreach.product, content_text=req.edited_body, content_type="lead_outreach_email",
    )
    outreach.compliance_status = "passed" if comp.passed else "flagged"
    outreach.compliance_score = comp.score
    outreach.status = new_status  # always back to human_review -- never auto-approved

    hitl_service.record_decision(
        db, asset_id=outreach.id, asset_type="lead_outreach", decision="edit",
        previous_status=previous_status, new_status=new_status, reviewer=req.reviewer,
        reason_tag=outreach.reason_tag, notes=outreach.notes,
        original_content=original_body, edited_content=req.edited_body,
        compliance_score=outreach.compliance_score,
    )
    db.commit()
    db.refresh(outreach)
    return LeadOutreachResponse.from_orm_with_json(outreach)

@router.post("/outreach/{outreach_id}/send", response_model=LeadOutreachResponse)
async def send_lead_outreach(outreach_id: int, db: Session = Depends(get_db)):
    """
    Sends an outreach email -- but ONLY if status=="approved" AND
    compliance_status=="passed" (hitl_service.is_publishable(), the exact same
    two-part gate the real LinkedIn publish endpoint uses). A human is allowed
    to "approve" a compliance-flagged draft as a sign-off that they've seen the
    warnings (see hitl_service's state machine docstring), but that alone must
    never be enough to actually send -- both conditions are mandatory here,
    same as everywhere else content leaves this system. pending/human_review/
    rejected/edited-but-not-reapproved outreach is rejected outright either
    way. Also refuses if the lead has no real, publicly-sourced email address
    on file (Lead.email is intentionally left blank rather than fabricated --
    see lead_service's discovery logic) -- there is nothing genuine to send to.

    Uses EMAIL_PROVIDER (default "mock", never sends a real email) -- see
    app.services.email_provider. Never marks send_status="sent" without a real
    provider call actually succeeding.
    """
    outreach = db.get(LeadOutreach, outreach_id)
    if not outreach:
        raise HTTPException(status_code=404, detail="Outreach draft not found")

    if not hitl_service.is_publishable(outreach.status, outreach.compliance_status):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot send outreach #{outreach_id} unless status=='approved' AND "
                f"compliance_status=='passed'. Current: status='{outreach.status}', "
                f"compliance_status='{outreach.compliance_status}'."
            ),
        )

    lead = db.get(Lead, outreach.lead_id)
    if not lead or not lead.email:
        raise HTTPException(
            status_code=400,
            detail="This lead has no verified email address on file -- outreach was never fabricated "
                   "contact info, so there is nothing real to send to.",
        )

    provider = get_email_provider()
    try:
        result = await provider.send(to=lead.email, subject=outreach.subject, body=outreach.body)
        outreach.send_status = "sent"
        outreach.send_error = None
        outreach.sent_at = datetime.now(timezone.utc)
        outreach.notes = f"{outreach.notes or ''} | Sent via {result['provider']} (message_id={result['message_id']})".strip(" |")
    except EmailSendError as e:
        outreach.send_status = "failed"
        outreach.send_error = e.message
    except Exception as e:
        outreach.send_status = "failed"
        outreach.send_error = str(e)

    db.commit()
    db.refresh(outreach)
    return LeadOutreachResponse.from_orm_with_json(outreach)

@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@router.post("/{lead_id}/enrich", response_model=LeadResponse)
async def enrich_lead(lead_id: int, req: EnrichLeadRequest = EnrichLeadRequest()):
    """
    Enrich an existing lead record.
    If source_url is supplied, scrapes and analyzes the company website to verify offerings and risk factors.
    Updates 5-factor score explanations and generates personalized outreach.
    """
    try:
        enriched_lead = await lead_service.enrich_lead(lead_id=lead_id, source_url=req.source_url)
        return enriched_lead
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lead enrichment failed: {str(e)}")

@router.post("/{lead_id}/outreach/generate", response_model=LeadOutreachResponse, status_code=201)
async def generate_structured_lead_outreach(lead_id: int, db: Session = Depends(get_db)):
    """
    Generates a structured, compliance-checked outreach draft (subject + body +
    personalization points + source evidence, all derived from the lead's own
    stored fields -- never fabricated) and enters it into human review. NEVER
    auto-approved, mirroring ContentQueue's exact governance pattern. This is the
    governed counterpart to the plain-string POST /{lead_id}/outreach below (kept
    for backward compatibility, but that endpoint bypasses compliance entirely).
    """
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    draft = lead_service.generate_structured_outreach(lead)

    comp = await compliance_service.evaluate_content(
        brand=draft["product"], content_text=draft["body"], content_type="lead_outreach_email",
    )
    compliance_status = "passed" if comp.passed else "flagged"
    status = "human_review" if comp.passed else "pending"

    outreach = LeadOutreach(
        lead_id=lead.id,
        product=draft["product"],
        subject=draft["subject"],
        body=draft["body"],
        original_body=draft["body"],
        personalization_points=json.dumps(draft["personalization_points"]),
        source_evidence=json.dumps(draft["source_evidence"]),
        compliance_status=compliance_status,
        status=status,
        compliance_score=comp.score,
        notes=comp.overall_feedback,
    )
    db.add(outreach)
    db.commit()
    db.refresh(outreach)
    return LeadOutreachResponse.from_orm_with_json(outreach)

@router.get("/{lead_id}/outreach", response_model=List[LeadOutreachResponse])
def list_lead_outreach(lead_id: int, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return [LeadOutreachResponse.from_orm_with_json(o) for o in lead.outreach_drafts]

@router.post("/{lead_id}/outreach")
def generate_lead_outreach(lead_id: int, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    brand = lead.recommended_brand or "doctorshield"
    outreach = lead_service.generate_outreach(
        prospect_name=lead.name,
        company=lead.company,
        brand=brand,
        industry=lead.industry,
        location=lead.location
    )
    lead.outreach_draft = outreach
    db.commit()
    db.refresh(lead)
    return {"lead_id": lead.id, "outreach_draft": outreach}

@router.post("", response_model=LeadResponse, status_code=201)
def create_lead(lead_in: LeadCreate, db: Session = Depends(get_db)):
    lead = Lead(**lead_in.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead

@router.patch("/{lead_id}/status", response_model=LeadResponse)
def update_lead_status(lead_id: int, status: str, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.status = status
    db.commit()
    db.refresh(lead)
    return lead
