from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from app.database.session import get_db
from app.models.entities import Competitor
from app.schemas.dtos import CompetitorCreate, CompetitorResponse
from app.services.research_service import research_service

router = APIRouter(prefix="/competitors", tags=["Competitor Intelligence"])

class CompetitorAnalyzeRequest(BaseModel):
    url: str
    brand: Optional[str] = "jade"

@router.get("", response_model=List[CompetitorResponse])
def list_competitors(
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    query = select(Competitor)
    if category:
        query = query.where(Competitor.category == category)
    query = query.order_by(desc(Competitor.collected_at)).limit(limit)
    return db.execute(query).scalars().all()

@router.get("/{comp_id}", response_model=CompetitorResponse)
def get_competitor(comp_id: int, db: Session = Depends(get_db)):
    comp = db.get(Competitor, comp_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Competitor record not found")
    return comp

@router.post("/analyze-url", response_model=CompetitorResponse)
async def analyze_competitor_url(req: CompetitorAnalyzeRequest, db: Session = Depends(get_db)):
    """
    Supplied URL flow:
    1. Scrapes the page
    2. Analyzes messaging, claims, offerings
    3. Extracts strategic counter-positioning whitespace
    4. Upserts competitor record in SQLite
    5. Returns the updated competitor entity
    """
    scraped = await research_service.scrape_url(req.url)
    if scraped.get("status") != "success":
        raise HTTPException(
            status_code=400,
            detail=f"Failed to scrape URL: {scraped.get('summary', 'Invalid or unreachable website')}"
        )
    
    finding = await research_service.analyze_scraped_content(scraped, brand=req.brand)
    research_service._save_or_update_competitor(req.brand or "jade", req.url, finding)
    
    comp = db.query(Competitor).filter(Competitor.url == req.url).first()
    if not comp:
        raise HTTPException(status_code=500, detail="Failed to retrieve saved competitor record")
    return comp

@router.post("", response_model=CompetitorResponse, status_code=201)
def create_competitor(comp_in: CompetitorCreate, db: Session = Depends(get_db)):
    comp = Competitor(**comp_in.model_dump())
    db.add(comp)
    db.commit()
    db.refresh(comp)
    return comp
