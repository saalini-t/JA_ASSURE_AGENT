import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agentic.orchestrator import run_agentic_pipeline
from app.config import EVIDENCE_DIR

router = APIRouter(prefix="/autonomous", tags=["Autonomous Pipeline"])
logger = logging.getLogger("nexora.api.autonomous")

class AutonomousRunRequest(BaseModel):
    brand: str = "jade"
    topic: str = "Why specialised agreed-value insurance considerations matter for jewellery businesses"
    platform: str = "linkedin"
    format_type: str = "auto" # "video", "image", "blog", "carousel", "auto"
    target_persona: str = "Independent Jeweller and High-Value Collector"
    force_regenerate_video: bool = False
    dry_run: bool = False

@router.post("/run")
def run_autonomous_campaign_endpoint(req: AutonomousRunRequest):
    """
    Executes the complete 12-agent LangGraph workflow natively for Nexora -> JA Assure.
    Architecture:
    Memory Retrieval -> Strategy Formulation -> Master Content -> Repurposer -> Media Decision Engine ->
    A/B Experimentation -> Compliance Gate -> Auto Approval -> The Hands (LinkedIn Publish) ->
    Database Persistence -> Feedback Learner -> Evidence Report Generation.
    """
    try:
        res = run_agentic_pipeline(
            brand_id=req.brand,
            topic=req.topic,
            platform=req.platform,
            format_type=req.format_type,
            autonomous_mode=True,
            dry_run=req.dry_run,
            force_regenerate_video=req.force_regenerate_video
        )
        return res
    except Exception as e:
        logger.error(f"Autonomous agentic run failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/evidence")
def list_evidence():
    """
    Lists generated evidence files and PDF report location.
    """
    pdf_file = EVIDENCE_DIR / "Nexora_JA_Assure_Autonomous_Execution_Evidence_Report.pdf"
    audit_files = list((EVIDENCE_DIR / "audit").glob("*.json")) if (EVIDENCE_DIR / "audit").exists() else []
    api_files = list((EVIDENCE_DIR / "api-responses").glob("*.json")) if (EVIDENCE_DIR / "api-responses").exists() else []

    return {
        "pdf_report_exists": pdf_file.exists(),
        "pdf_report_url": "/evidence/Nexora_JA_Assure_Autonomous_Execution_Evidence_Report.pdf" if pdf_file.exists() else None,
        "audit_logs_count": len(audit_files),
        "api_responses_count": len(api_files),
        "evidence_root": str(EVIDENCE_DIR)
    }
