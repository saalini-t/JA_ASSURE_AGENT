from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class ContentQueue(Base):
    __tablename__ = "content_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    brand: Mapped[str] = mapped_column(String(50), index=True, nullable=False) # jade, doctorshield, jaguartransit
    platform: Mapped[str] = mapped_column(String(50), index=True, nullable=False) # linkedin, instagram, facebook, tiktok, etc.
    content_type: Mapped[str] = mapped_column(String(50), default="post") # post, reel, carousel, article, ad
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    content_raw: Mapped[str] = mapped_column(Text, nullable=False)
    variation: Mapped[str] = mapped_column(String(50), default="A") # A, B, default
    language: Mapped[str] = mapped_column(String(10), default="en") # en, ms, id, th, zh
    compliance_status: Mapped[str] = mapped_column(String(50), default="pending", index=True) # pending, passed, flagged, failed
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True) # pending, compliance_checked, human_review, approved, rejected, scheduled, published
    compliance_score: Mapped[float] = mapped_column(Float, default=0.0)
    reason_tag: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) # compliance or rejection reason
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # video script, prompt metadata, etc.
    # Immutable snapshot of the very first AI-generated text. Set once, never overwritten,
    # so the original generation survives any number of human edits/rewrites/regenerations.
    original_content_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    feedbacks: Mapped[List["Feedback"]] = relationship("Feedback", back_populates="content_item", cascade="all, delete-orphan")
    publishing_records: Mapped[List["PublishingRecord"]] = relationship("PublishingRecord", back_populates="content_item", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_content_brand_platform", "brand", "platform"),
        Index("ix_content_status_compliance", "status", "compliance_status"),
    )


class Competitor(Base):
    __tablename__ = "competitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False) # jewellery, medical, transit, etc.
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    detected_change: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actionable_recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    relevance: Mapped[float] = mapped_column(Float, default=0.5)
    source: Mapped[str] = mapped_column(String(100), default="public_web")
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    @property
    def source_type(self) -> str:
        if self.source in ["VERIFIED_SOURCE", "AI_ANALYSIS", "DEMO_DATA"]:
            return self.source
        if "live" in (self.source or "").lower() or (self.url and "http" in self.url):
            return "VERIFIED_SOURCE"
        return "DEMO_DATA"

    snapshots: Mapped[List["CompetitorSnapshot"]] = relationship(
        "CompetitorSnapshot", back_populates="competitor", cascade="all, delete-orphan",
        order_by="CompetitorSnapshot.captured_at",
    )


class CompetitorSnapshot(Base):
    """
    Immutable point-in-time capture of a competitor's researched state. The
    `Competitor` row above is a denormalized "latest state" cache (unchanged,
    upserted in place for backward compatibility); this table is the append-only
    history that makes "compare current vs. previous" and change-detection digests
    possible at all -- the upsert-only design had no way to answer "what changed
    since last time" because it always overwrote the only copy.
    """
    __tablename__ = "competitor_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(Integer, ForeignKey("competitors.id", ondelete="CASCADE"), index=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), default="DEMO_DATA")  # VERIFIED_SOURCE | AI_ANALYSIS | DEMO_DATA
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    detected_change: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actionable_recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)

    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="snapshots")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False) # Contact / Key Person
    company: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    industry: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    company_size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    fit_score: Mapped[float] = mapped_column(Float, default=0.0) # 0 to 100
    qualification_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommended_brand: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # jade, doctorshield, jaguartransit
    outreach_draft: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), default="prospecting")
    status: Mapped[str] = mapped_column(String(50), default="new", index=True) # new, contacted, qualified, converted, archived
    scoring_breakdown_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    outreach_drafts: Mapped[List["LeadOutreach"]] = relationship(
        "LeadOutreach", back_populates="lead", cascade="all, delete-orphan",
        order_by="LeadOutreach.created_at",
    )

    @property
    def source_type(self) -> str:
        if self.source in ["VERIFIED_SOURCE", "AI_GENERATED_PROSPECT", "DEMO_DATA"]:
            return self.source
        if "prospect" in (self.source or "").lower() or "agent" in (self.source or "").lower():
            return "AI_GENERATED_PROSPECT"
        if self.source and "http" in self.source:
            return "VERIFIED_SOURCE"
        return "DEMO_DATA"

    @property
    def scoring_breakdown(self) -> Optional[dict]:
        """Real 5-factor breakdown from the last score calculation, or None if this
        lead predates the field / was created manually without scoring -- never
        approximated client-side from fit_score alone."""
        if not self.scoring_breakdown_json:
            return None
        import json
        return json.loads(self.scoring_breakdown_json)


class LeadOutreach(Base):
    """
    Governed outreach draft for a Lead -- the SAME HITL/compliance gate that guards
    ContentQueue guards this, reusing hitl_service's generic asset_type/asset_id
    primitives exactly as ReviewDecision's own docstring originally intended ("so
    the Lead/Outreach workflow... can route their own approve/reject/edit actions
    through the exact same primitives... without inventing a second governance
    mechanism"). Kept separate from Lead (the prospect/company record) so
    re-enriching/re-scoring a lead never disturbs outreach review history, and so a
    lead can have multiple outreach attempts over time.
    """
    __tablename__ = "lead_outreach"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    product: Mapped[str] = mapped_column(String(50), nullable=False)  # jade, doctorshield, jaguartransit
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Immutable snapshot of the first-generated body, mirrors ContentQueue.original_content_raw.
    original_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    personalization_points: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list of strings
    source_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list of strings
    compliance_status: Mapped[str] = mapped_column(String(50), default="pending", index=True)  # pending, passed, flagged
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)  # pending, human_review, approved, rejected
    compliance_score: Mapped[float] = mapped_column(Float, default=0.0)
    reason_tag: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Send tracking -- entirely separate from `status` (the HITL approval state).
    # An outreach can be "approved" and still sit at send_status="draft" forever
    # if no email provider is configured; only a genuine provider success sets
    # "sent". Never set to "sent" without a real (mock or SMTP) provider call.
    send_status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, sent, failed
    send_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    lead: Mapped["Lead"] = relationship("Lead", back_populates="outreach_drafts")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    content_id: Mapped[int] = mapped_column(Integer, ForeignKey("content_queue.id", ondelete="CASCADE"), index=True)
    reason_tag: Mapped[str] = mapped_column(String(100), index=True, nullable=False) # e.g. "claim_unsubstantiated", "tone_off", "pricing_disclaimer_missing"
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    original_content: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    content_item: Mapped["ContentQueue"] = relationship("ContentQueue", back_populates="feedbacks")


class LessonLearned(Base):
    __tablename__ = "lessons_learned"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False) # compliance, tone, platform, audience
    lesson: Mapped[str] = mapped_column(Text, nullable=False)
    examples: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    frequency: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    @property
    def lesson_rule(self) -> str:
        return self.lesson

    @property
    def is_active(self) -> bool:
        return self.active


class Analytics(Base):
    __tablename__ = "analytics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    metric_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    brand: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)
    platform: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)
    metric_value: Mapped[float] = mapped_column(Float, default=0.0)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class PublishingRecord(Base):
    __tablename__ = "publishing_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    content_id: Mapped[int] = mapped_column(Integer, ForeignKey("content_queue.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    # 1-based attempt number for this (content_id, platform) publish effort. Each retry
    # of a transient failure gets its OWN row (immutable audit trail) rather than
    # overwriting a prior attempt's error_info -- see publishing_service.py.
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    external_post_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), index=True, default="scheduled") # scheduled, publishing, published, failed
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    engagement_metrics: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON string of impressions, clicks, etc.
    error_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    content_item: Mapped["ContentQueue"] = relationship("ContentQueue", back_populates="publishing_records")


class ReviewDecision(Base):
    """
    Immutable audit log of every human-in-the-loop decision made on any governed asset.
    Deliberately polymorphic (asset_type + asset_id, no FK) so the SAME HITL boundary can
    eventually govern the Content Queue, Lead/Outreach drafts, and Competitor recommendations
    without a schema change per workflow. For today's Content Queue usage, asset_id == content_queue.id.
    """
    __tablename__ = "review_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    asset_type: Mapped[str] = mapped_column(String(50), index=True, default="content_queue") # content_queue, lead_outreach, competitor_recommendation
    asset_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    reviewer: Mapped[str] = mapped_column(String(100), default="compliance_officer")
    decision: Mapped[str] = mapped_column(String(50), index=True, nullable=False) # approve, reject, edit, rewrite, regenerate
    reason_tag: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    original_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # version immediately before this decision
    edited_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # version immediately after this decision (edit/rewrite/regenerate only)
    compliance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    previous_status: Mapped[str] = mapped_column(String(50), nullable=False)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)

    __table_args__ = (
        Index("ix_review_decisions_asset", "asset_type", "asset_id"),
    )
