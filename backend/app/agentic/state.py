from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class AgentExecutionLog(BaseModel):
    agent_name: str
    status: str
    timestamp: str
    action: str
    details: str
    metadata: Optional[Dict[str, Any]] = None

class AgenticPipelineInput(BaseModel):
    brand_id: str = "jade"
    topic: str
    audience_key: str = "jeweller"
    objective_id: str = "educate"
    platform: str = "linkedin"
    autonomous_mode: bool = True
    dry_run: bool = False
    force_regenerate_video: bool = False

class AgenticState(BaseModel):
    item_id: str
    brand_id: str
    brand_name: str
    topic: str
    audience_key: str
    objective_id: str
    platform: str = "linkedin"
    autonomous_mode: bool = True
    dry_run: bool = False
    
    # Internal context
    brand_dna_prompt: str = ""
    audience_context: str = ""
    objective_context: str = ""
    lessons_prompt: str = ""
    lesson_ids: List[str] = []
    
    # Agent logs
    agent_logs: List[Dict[str, Any]] = []
    
    # Generated deliverables
    message_strategy: Dict[str, Any] = {}
    master_content: Dict[str, Any] = {}
    adaptations: Dict[str, Any] = {}
    media_result: Dict[str, Any] = {}
    ab_experiment: Dict[str, Any] = {}
    compliance_audit: Dict[str, Any] = {}
    compliance_correction_attempts: int = 0
    
    # Approval & Publishing
    approval_status: str = "pending_review"
    approved_by: Optional[str] = None
    human_approved: bool = False
    publishing_result: Dict[str, Any] = {}
    
    # Database and Evidence
    db_content_id: Optional[int] = None
    db_publishing_id: Optional[int] = None
    evidence_pdf_path: Optional[str] = None
    
    status: str = "in_progress"
    human_edits: List[Dict[str, Any]] = []
    final_text: Optional[str] = None
    created_at: str
    updated_at: str
