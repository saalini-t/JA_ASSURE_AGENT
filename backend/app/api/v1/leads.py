from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from app.database.session import get_db
from app.models.entities import Lead
from app.schemas.dtos import LeadCreate, LeadResponse
from app.schemas.agent_contracts import LeadProspect
from app.services.lead_service import lead_service

router = APIRouter(prefix="/leads", tags=["Lead Generation & Scoring"])

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
