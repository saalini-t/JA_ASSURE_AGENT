from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.schemas.agent_contracts import ComplianceResult
from app.services.compliance.rules import COMPLIANCE_RULES_REGISTRY
from app.services.compliance_service import compliance_service

router = APIRouter(prefix="/compliance", tags=["Compliance Gate"])

class ComplianceCheckRequest(BaseModel):
    brand: str = "jade"
    content_text: str
    content_type: str = "post"
    product: Optional[str] = None
    country: Optional[str] = None
    jurisdiction: Optional[str] = None
    platform: Optional[str] = None
    language: Optional[str] = None

@router.post("/check", response_model=ComplianceResult)
async def check_compliance(req: ComplianceCheckRequest):
    """
    Run the mandatory insurance compliance gate on any marketing copy.
    Returns pass/fail status, regulatory violations, suggestions, severity, and penalty score.
    """
    try:
        result = await compliance_service.evaluate_content(
            brand=req.brand,
            content_text=req.content_text,
            content_type=req.content_type,
            product=req.product,
            country=req.country,
            jurisdiction=req.jurisdiction,
            platform=req.platform,
            language=req.language
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compliance check failed: {str(e)}")

@router.post("/rewrite")
async def rewrite_compliance(req: ComplianceCheckRequest):
    """
    Compliance Rewrite Workflow:
    Identifies regulatory violations, rewrites compliant replacement copy,
    and MANDATES AN INDEPENDENT RE-CHECK through the compliance engine.
    """
    try:
        rewrite_result = await compliance_service.rewrite_non_compliant_content(
            brand=req.brand,
            original_text=req.content_text,
            content_type=req.content_type,
            product=req.product,
            country=req.country,
            jurisdiction=req.jurisdiction,
            platform=req.platform,
            language=req.language
        )
        return rewrite_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compliance rewrite failed: {str(e)}")

@router.get("/rules")
def list_compliance_rules():
    """
    List all 12 regulatory compliance rules enforced by the gate with full category and severity metadata.
    """
    return [
        {
            "id": r.rule_id,
            "name": r.name,
            "category": r.category,
            "severity": r.severity.lower(),
            "penalty": r.penalty,
            "description": r.description,
            "explanation": r.explanation,
            "suggested_fix": r.suggested_fix,
            "brand_filter": r.brand_filter,
            "is_absence_rule": r.is_absence_rule
        }
        for r in COMPLIANCE_RULES_REGISTRY
    ]
