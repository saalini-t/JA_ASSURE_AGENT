import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .graph import MARKETING_AGENT_GRAPH, LangGraphContentState
from app.brand.registry import get_brand

logger = logging.getLogger("nexora.agentic.orchestrator")

def run_agentic_pipeline(
    brand_id: str,
    topic: str,
    audience_key: str = "jeweller",
    objective_id: str = "educate",
    platform: str = "linkedin",
    format_type: str = "auto",
    autonomous_mode: bool = True,
    dry_run: bool = False,
    force_regenerate_video: bool = False
) -> Dict[str, Any]:
    """
    Executes the complete 12-agent LangGraph workflow natively:
    1. Memory & Context Retrieval Agent
    2. Strategy Formulation Agent
    3. Master Narrative Content Agent
    4. Multi-Platform Repurposer Agent
    5. Media Decision Agent (Video Reuse -> Video Gen -> Image Fallback)
    6. Growth & Experimentation Agent (A/B testing)
    7. Compliance Gate Agent (MAS/PDPA Insurance Rubric + Auto-Correction Loop)
    8. Autonomous Approval Agent (AUTO_APPROVED / SYSTEM)
    9. The Hands: Publishing Agent (LinkedIn API / UGC Post)
    10. Database Persistence Agent (nexora_ja_assure.db)
    11. Feedback Memory Learner Agent
    12. Evidence Report Agent (HD PDF Evidence Report)
    """
    now = datetime.now(timezone.utc).isoformat() + "Z"
    item_id = f"NEXORA-AUTO-{int(datetime.now(timezone.utc).timestamp()) % 1000000:06d}"

    brand = get_brand(brand_id)

    initial_state: LangGraphContentState = {
        "item_id": item_id,
        "brand_id": brand.id,
        "brand_name": brand.name,
        "topic": topic,
        "audience_key": audience_key,
        "objective_id": objective_id,
        "platform": platform,
        "format_type": format_type,
        "autonomous_mode": autonomous_mode,
        "dry_run": dry_run,
        "force_regenerate_video": force_regenerate_video,
        
        "brand_dna_prompt": "",
        "audience_context": "",
        "objective_context": "",
        "lessons_prompt": "",
        "lesson_ids": [],
        
        "agent_logs": [],
        "message_strategy": {},
        "master_content": {},
        "adaptations": {},
        "media_result": {},
        "ab_experiment": {},
        "compliance_audit": {},
        "compliance_correction_attempts": 0,
        
        "approval_status": "pending_review",
        "approved_by": None,
        "human_approved": False,
        "publishing_result": {},
        
        "db_content_id": None,
        "db_publishing_id": None,
        "evidence_pdf_path": None,
        
        "status": "in_progress",
        "human_edits": [],
        "final_text": None,
        "created_at": now,
        "updated_at": now
    }

    logger.info(f"Invoking complete 12-agent LangGraph execution for {brand.name}: '{topic}'...")
    final_state = MARKETING_AGENT_GRAPH.invoke(initial_state)

    content_item = {
        "id": item_id,
        "db_content_id": final_state.get("db_content_id"),
        "db_publishing_id": final_state.get("db_publishing_id"),
        "brand_id": final_state["brand_id"],
        "brand_name": final_state["brand_name"],
        "topic": final_state["topic"],
        "audience_id": final_state["audience_key"],
        "objective_id": final_state["objective_id"],
        "status": final_state["status"],
        "agent_logs": final_state.get("agent_logs", []),
        "message_strategy": final_state["message_strategy"],
        "master_content": final_state["master_content"],
        "adaptations": final_state["adaptations"],
        "media_result": final_state.get("media_result", {}),
        "ab_experiment": final_state["ab_experiment"],
        "quality_audits": {
            "linkedin": final_state["compliance_audit"],
            "instagram": final_state["compliance_audit"],
            "x": final_state["compliance_audit"]
        },
        "compliance_audit": final_state["compliance_audit"],
        "approval_status": final_state["approval_status"],
        "approved_by": final_state["approved_by"],
        "human_approved": final_state["human_approved"],
        "publishing_result": final_state.get("publishing_result", {}),
        "evidence_pdf_path": final_state.get("evidence_pdf_path"),
        "lessons_applied": final_state.get("lesson_ids", []),
        "final_text": final_state.get("final_text", ""),
        "created_at": final_state["created_at"],
        "updated_at": final_state["updated_at"]
    }

    return content_item
