from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from app.schemas.agent_contracts import (
    ResearchInsight,
    CompetitorInsight,
    ContentBrief,
    GeneratedVariation,
    ComplianceResult,
    ComplianceViolation,
    HumanReviewAction,
    FeedbackRecord,
    LessonLearned,
    LeadProspect,
    PublishingSchedule,
    LeadScoringBreakdown,
)

# ----------------- Content Queue DTOs -----------------
class ContentQueueBase(BaseModel):
    brand: str
    platform: str
    content_type: str = "post"
    topic: str
    content_raw: str
    variation: str = "A"
    language: str = "en"
    compliance_status: str = "pending"
    status: str = "pending"
    compliance_score: float = 0.0
    reason_tag: Optional[str] = None
    notes: Optional[str] = None
    metadata_json: Optional[str] = None

class ContentQueueCreate(ContentQueueBase):
    pass

class ContentQueueUpdate(BaseModel):
    """
    Metadata-only patch DTO. Deliberately excludes `status`, `compliance_status`,
    `compliance_score`, and `content_raw` — those fields are HITL-governed and may only
    change through the dedicated /queue/{id}/approve|reject|edit|rewrite|regenerate
    actions, which route through app.services.hitl_service. This is what prevents a
    direct PATCH from fabricating an "approved" or "passed" asset. See hitl_service.py.
    """
    brand: Optional[str] = None
    platform: Optional[str] = None
    content_type: Optional[str] = None
    topic: Optional[str] = None
    variation: Optional[str] = None
    language: Optional[str] = None
    reason_tag: Optional[str] = None
    notes: Optional[str] = None
    metadata_json: Optional[str] = None

class ContentQueueResponse(ContentQueueBase):
    id: int
    original_content_raw: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ----------------- Review Decision DTOs (HITL audit trail) -----------------
class ReviewDecisionResponse(BaseModel):
    id: int
    asset_type: str
    asset_id: int
    reviewer: str
    decision: str
    reason_tag: Optional[str] = None
    notes: Optional[str] = None
    original_content: Optional[str] = None
    edited_content: Optional[str] = None
    compliance_score: Optional[float] = None
    previous_status: str
    new_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ----------------- Competitor DTOs -----------------
class CompetitorBase(BaseModel):
    name: str
    url: Optional[str] = None
    category: str
    title: str
    summary: str
    detected_change: Optional[str] = None
    actionable_recommendation: Optional[str] = None
    relevance: float = 0.5
    source: str = "public_web"

class CompetitorCreate(CompetitorBase):
    pass

class CompetitorResponse(CompetitorBase):
    id: int
    collected_at: datetime
    # Computed read-only property on the Competitor model (derived from `source`) --
    # deliberately absent from CompetitorBase/Create: passing it through to the
    # SQLAlchemy constructor crashes, since the model has no setter for it.
    source_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CompetitorSnapshotResponse(BaseModel):
    id: int
    competitor_id: int
    source_url: Optional[str] = None
    source_type: str
    title: str
    summary: str
    detected_change: Optional[str] = None
    actionable_recommendation: Optional[str] = None
    captured_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompetitorDigestEntry(BaseModel):
    """
    One digest entry per requirement: competitor, what changed, source, previous
    state, current state, detected date, why it matters, suggested action. Never
    presents speculation as fact -- has_change is a factual text-diff result, not
    an AI judgment call about business significance.
    """
    competitor_id: int
    competitor_name: str
    category: str
    source_url: Optional[str] = None
    source_type: str
    has_change: bool
    changed_fields: List[str] = Field(default_factory=list)
    previous_state: Optional[Dict[str, Any]] = None
    current_state: Dict[str, Any]
    detected_at: datetime
    why_it_matters: Optional[str] = None
    suggested_action: Optional[str] = None
    note: Optional[str] = None  # e.g. "baseline snapshot -- no prior snapshot to compare"

# ----------------- Lead DTOs -----------------
class LeadBase(BaseModel):
    name: str
    company: str
    industry: str
    email: Optional[str] = None
    location: Optional[str] = None
    company_size: Optional[str] = None
    fit_score: float = 0.0
    qualification_reason: Optional[str] = None
    recommended_brand: Optional[str] = None
    outreach_draft: Optional[str] = None
    source: Optional[str] = "prospecting"
    status: str = "new"

class LeadCreate(LeadBase):
    pass

class LeadResponse(LeadBase):
    id: int
    created_at: datetime
    # Computed read-only property on the Lead model (derived from `source`) --
    # deliberately absent from LeadBase/Create: same bug class as Competitor's
    # source_type (passing it through to the SQLAlchemy constructor crashes,
    # since the model has no setter for it).
    source_type: Optional[str] = None
    # Real 5-factor breakdown from the last score calculation -- None (never
    # approximated) for leads created before this field existed or via the
    # plain manual-create endpoint, which has no scoring pass to draw from.
    scoring_breakdown: Optional[LeadScoringBreakdown] = None

    model_config = ConfigDict(from_attributes=True)


# ----------------- Lead Outreach DTOs (governed by compliance + HITL) -----------------
class LeadOutreachResponse(BaseModel):
    id: int
    lead_id: int
    product: str
    subject: str
    body: str
    original_body: Optional[str] = None
    personalization_points: List[str] = Field(default_factory=list)
    source_evidence: List[str] = Field(default_factory=list)
    compliance_status: str
    status: str
    compliance_score: float
    reason_tag: Optional[str] = None
    notes: Optional[str] = None
    send_status: str = "draft"
    send_error: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_json(cls, obj) -> "LeadOutreachResponse":
        import json
        return cls(
            id=obj.id, lead_id=obj.lead_id, product=obj.product, subject=obj.subject, body=obj.body,
            original_body=obj.original_body,
            personalization_points=json.loads(obj.personalization_points) if obj.personalization_points else [],
            source_evidence=json.loads(obj.source_evidence) if obj.source_evidence else [],
            compliance_status=obj.compliance_status, status=obj.status, compliance_score=obj.compliance_score,
            reason_tag=obj.reason_tag, notes=obj.notes,
            send_status=obj.send_status, send_error=obj.send_error, sent_at=obj.sent_at,
            created_at=obj.created_at, updated_at=obj.updated_at,
        )

# ----------------- Feedback DTOs -----------------
class FeedbackCreate(BaseModel):
    content_id: int
    reason_tag: str
    notes: str
    original_content: str
    corrected_content: Optional[str] = None

class FeedbackResponse(FeedbackCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ----------------- Lessons Learned DTOs -----------------
class LessonLearnedCreate(BaseModel):
    category: str
    lesson: str
    examples: Optional[str] = None
    frequency: int = 1
    active: bool = True

class LessonLearnedResponse(LessonLearnedCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ----------------- Analytics DTOs -----------------
class AnalyticsMetricCreate(BaseModel):
    metric_name: str
    brand: Optional[str] = None
    platform: Optional[str] = None
    metric_value: float
    metadata_json: Optional[str] = None

class AnalyticsMetricResponse(AnalyticsMetricCreate):
    id: int
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DashboardSummary(BaseModel):
    total_content: int
    pending_compliance: int
    pending_human_review: int
    compliance_approved: int
    human_approved: int
    approved: int # alias to human_approved
    rejected: int
    edited: int = 0
    published: int
    approval_rate: float = 0.0
    rejection_rate: float = 0.0
    average_compliance_score: float
    total_leads: int
    average_lead_score: float
    total_lessons_learned: int
    active_lessons_count: int = 0
    total_feedback_count: int = 0
    regeneration_count: int = 0
    brand_breakdown: Dict[str, int]
    platform_breakdown: Dict[str, int]
    language_breakdown: Dict[str, int]
    feedback_reason_frequency: Dict[str, int]
    compliance_score_distribution: Dict[str, int] = Field(default_factory=dict)
    lead_score_distribution: Dict[str, int] = Field(default_factory=dict)
    status_breakdown: Dict[str, int] = Field(default_factory=dict)

# ----------------- Publishing DTOs -----------------
class PublishingRecordBase(BaseModel):
    content_id: int
    platform: str
    attempt: int = 1
    external_post_id: Optional[str] = None
    status: str = "scheduled"
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    engagement_metrics: Optional[str] = None
    error_info: Optional[str] = None

class PublishingRecordCreate(PublishingRecordBase):
    pass

class PublishingRecordResponse(PublishingRecordBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
