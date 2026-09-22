from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

# ========================================================
# 1. Research & Competitor Insights
# ========================================================

class CompetitorInsight(BaseModel):
    competitor_name: str
    category: str
    key_messaging: str
    detected_change: Optional[str] = None
    opportunity: Optional[str] = None
    threat_level: str = "medium" # low, medium, high
    source_url: Optional[str] = None
    market_country: Optional[str] = None
    offerings: List[str] = Field(default_factory=list)
    positioning: Optional[str] = None
    notable_claims: List[str] = Field(default_factory=list)
    content_themes: List[str] = Field(default_factory=list)
    source_type: str = "DEMO_DATA" # VERIFIED_SOURCE, AI_ANALYSIS, DEMO_DATA
    confidence: float = 0.85
    last_researched: Optional[str] = None

class ResearchFinding(BaseModel):
    source: Optional[str] = None
    source_type: str = "AI_ANALYSIS" # VERIFIED_SOURCE, AI_ANALYSIS, DEMO_DATA
    title: str
    company: str
    category: str = "general" # jewellery, medical, transit, general
    market_country: Optional[str] = None
    summary: str
    offerings: List[str] = Field(default_factory=list)
    positioning: Optional[str] = None
    target_audience: Optional[str] = None
    notable_claims: List[str] = Field(default_factory=list)
    content_opportunities: List[str] = Field(default_factory=list)
    potential_weaknesses: List[str] = Field(default_factory=list)
    counter_positioning: Optional[str] = None # Whitespace / opportunity for JA Assure
    confidence: float = 0.85

class ResearchInsight(BaseModel):
    brand: str # jade, doctorshield, jaguartransit
    topic: str
    market_context: str
    target_audience: str
    pain_points: List[str] = Field(default_factory=list)
    competitor_insights: List[CompetitorInsight] = Field(default_factory=list)
    recommended_angles: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    findings: List[ResearchFinding] = Field(default_factory=list)


# ========================================================
# 2. Content Generation Contracts
# ========================================================

class ContentBrief(BaseModel):
    brand: str
    platform: str # linkedin, instagram, facebook, tiktok, twitter, blog
    content_type: str = "post" # post, reel, carousel, article, thread
    topic: str
    target_persona: Optional[str] = None
    tone_guidelines: Optional[str] = None
    key_benefits: List[str] = Field(default_factory=list)
    cta: Optional[str] = None
    language: str = "en" # en, ms, id, th, zh
    variations_count: int = 2
    context_lessons: List[str] = Field(default_factory=list) # Lessons learned injected from past human feedback

class GeneratedVariation(BaseModel):
    variation_label: str # e.g. "A", "B"
    content_text: str
    headline: Optional[str] = None
    hashtags: List[str] = Field(default_factory=list)
    cta: Optional[str] = None
    media_prompt: Optional[str] = None # prompt for AI image or video storyboard


# ========================================================
# 3. Compliance Gate Contracts
# ========================================================

class ClaimItem(BaseModel):
    claim_text: str
    claim_type: str = "general_marketing" # guaranteed_outcome, coverage, pricing, medical, comparative, numerical, etc.
    risk_level: str = "low" # critical, high, medium, low
    explanation: Optional[str] = None

class ComplianceViolation(BaseModel):
    rule_id: str
    category: Optional[str] = None
    severity: str = "medium" # critical, high, medium, low (also accepts warning, info)
    message: str = ""
    reason: Optional[str] = None
    flagged_phrase: Optional[str] = None
    matched_text: Optional[str] = None
    suggested_fix: Optional[str] = None
    recommendation: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if not self.reason and self.message:
            self.reason = self.message
        elif not self.message and self.reason:
            self.message = self.reason
        if not self.matched_text and self.flagged_phrase:
            self.matched_text = self.flagged_phrase
        elif not self.flagged_phrase and self.matched_text:
            self.flagged_phrase = self.matched_text
        if not self.recommendation and self.suggested_fix:
            self.recommendation = self.suggested_fix
        elif not self.suggested_fix and self.recommendation:
            self.suggested_fix = self.recommendation

class ComplianceResult(BaseModel):
    passed: bool
    score: float = Field(ge=0.0, le=100.0) # 0 to 100
    status: str = "BLOCKED" # PASS, WARNING, BLOCKED, REQUIRES_HUMAN_REVIEW
    violations: List[ComplianceViolation] = Field(default_factory=list)
    warnings: List[ComplianceViolation] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    overall_feedback: str = ""
    disclaimers_required: List[str] = Field(default_factory=list)
    disclaimer_status: Optional[str] = "compliant" # compliant, missing, incomplete
    claims_analyzed: List[ClaimItem] = Field(default_factory=list)
    jurisdiction: Optional[str] = "Singapore"
    brand: Optional[str] = None
    product: Optional[str] = None
    platform: Optional[str] = None
    language: Optional[str] = "en"
    human_review_required: bool = True


# ========================================================
# 4. Human Review & Feedback Loop Contracts
# ========================================================

class HumanReviewAction(BaseModel):
    content_id: int
    action: str # approve, reject, edit
    reason_tag: Optional[str] = None # e.g. "misleading_guarantee", "tone_off", "pricing_claim", "inaccurate_coverage"
    notes: Optional[str] = None
    corrected_content: Optional[str] = None
    reviewer: Optional[str] = "compliance_officer"

class FeedbackRecord(BaseModel):
    id: Optional[int] = None
    content_id: int
    reason_tag: str
    notes: str
    original_content: str
    corrected_content: Optional[str] = None
    created_at: Optional[datetime] = None

class LessonLearned(BaseModel):
    id: Optional[int] = None
    category: str # compliance, tone, brand_voice, regional_nuance
    lesson: str
    examples: Optional[str] = None
    frequency: int = 1
    active: bool = True

class SynthesizedLesson(BaseModel):
    lesson_rule: str
    rationale: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = "medium" # low, medium, high
    example_guidance: Optional[str] = None


# ========================================================
# 5. Lead Intelligence Contracts
# ========================================================

class LeadScoringBreakdown(BaseModel):
    industry_fit: float = Field(ge=0, le=25, description="Weight 25%: Industry alignment with JA Assure products")
    company_profile: float = Field(ge=0, le=20, description="Weight 20%: Size, reputation, transaction volume")
    geographic_relevance: float = Field(ge=0, le=20, description="Weight 20%: SG, MY, TH, ID jurisdiction presence")
    product_relevance: float = Field(ge=0, le=20, description="Weight 20%: Need for Jewellery, Med Indemnity, or Transit Cargo")
    potential_insurance_need: float = Field(ge=0, le=15, description="Weight 15%: Exposure to liability, theft, or port risk")
    total_fit_score: float = Field(ge=0, le=100)
    industry_fit_reason: Optional[str] = None
    company_profile_reason: Optional[str] = None
    geographic_relevance_reason: Optional[str] = None
    product_relevance_reason: Optional[str] = None
    potential_insurance_need_reason: Optional[str] = None

class LeadProspect(BaseModel):
    name: str
    company: str
    industry: str
    email: Optional[str] = None
    location: Optional[str] = None
    company_size: Optional[str] = None
    recommended_brand: Optional[str] = None # jade, doctorshield, jaguartransit
    fit_score: float = 0.0
    qualification_reason: Optional[str] = None
    outreach_draft: Optional[str] = None
    source: Optional[str] = "agent_prospector"
    source_type: str = "AI_GENERATED_PROSPECT" # VERIFIED_SOURCE, AI_GENERATED_PROSPECT, DEMO_DATA
    likely_decision_maker_role: Optional[str] = None
    insurance_need: Optional[str] = None
    risk_exposure: Optional[str] = None
    why_relevant: Optional[str] = None
    discovery_rationale: Optional[str] = None
    source_url: Optional[str] = None
    scoring_breakdown: Optional[LeadScoringBreakdown] = None

class DiscoveredProspectItem(BaseModel):
    company_name: str
    industry: str
    country_city: str
    company_profile: str
    likely_decision_maker_role: str
    insurance_need: str
    risk_exposure: str
    why_relevant: str
    discovery_rationale: str

class DiscoveredProspectList(BaseModel):
    prospects: List[DiscoveredProspectItem] = Field(default_factory=list)


# ========================================================
# 6. Video / Reels Contracts
# ========================================================

class VideoScene(BaseModel):
    scene_number: int
    duration_seconds: int = 10
    visual_description: str
    voiceover: str
    onscreen_text: str
    transition: Optional[str] = "Cut"
    compliance_disclaimer: Optional[str] = None

class VideoScript(BaseModel):
    brand: Optional[str] = "jade"
    title: Optional[str] = None
    concept: Optional[str] = None
    hook: Optional[str] = None
    target_duration_seconds: int = 45 # 30-60s
    voiceover_tone: Optional[str] = "Professional"
    target_platform: Optional[str] = "reel" # reel, video, tiktok, instagram
    target_audience: Optional[str] = None
    language: Optional[str] = "en"
    scenes: List[VideoScene] = Field(default_factory=list)
    cta: Optional[str] = None
    disclaimer: Optional[str] = None
    media_status: str = "ai_storyboard_generated" # ai_storyboard_generated, voice_generated, pending_render
    audio_url: Optional[str] = None
    audio_filename: Optional[str] = None
    audio_duration_seconds: Optional[float] = None
    voice_provider: Optional[str] = None
    voice_language: Optional[str] = None
    voice_status: Optional[str] = None

    # Phase 1 render result fields (populated by video_generation_service, not by Groq)
    job_id: Optional[str] = None
    video_url: Optional[str] = None
    video_duration_seconds: Optional[float] = None
    scenes_generated: Optional[int] = None
    image_source: Optional[str] = None # ai_generated_openai | huggingface | branded_fallback_demo | mixed (...)
    render_status: Optional[str] = None # completed | failed | skipped
    render_error: Optional[str] = None

    # Phase 2 render result fields (voiceover + captions; also populated by
    # video_generation_service, not by Groq). NOTE: audio_duration_seconds is shared
    # with the voice-agent field of the same name above -- both represent "how long
    # is the audio", populated by whichever path (standalone voice studio vs full
    # video render) actually ran.
    has_audio: Optional[bool] = None
    has_captions: Optional[bool] = None
    audio_source: Optional[str] = None # e.g. gtts | openai_tts
    caption_file: Optional[str] = None # URL to the generated .srt, served like video_url

    # Phase 2 (narration-duration budgeting) reporting fields -- populated by
    # video_generation_service when narrate=True; see narration_budget.py.
    narration_word_count: Optional[int] = None
    narration_estimated_seconds: Optional[float] = None
    narration_rewritten: Optional[bool] = None

    # Phase 3 (real AI visual generation) per-scene image provenance -- see
    # video_generation_service.SceneImageReport. Never claims a fallback card is
    # AI-generated: is_real_ai is explicitly false whenever source is the fallback.
    scene_image_sources: Optional[List[Dict[str, Any]]] = None
    ai_generated_scene_count: Optional[int] = None
    fallback_scene_count: Optional[int] = None

class VoiceConfig(BaseModel):
    language: str = "en"
    slow: bool = False
    tld: str = "com"
    provider: str = "gtts"

class VoiceGenerationResult(BaseModel):
    status: str = "generated"
    audio_url: str
    audio_filename: str
    language: str
    provider: str = "gtts"
    duration_seconds: Optional[float] = None
    voiceover_text: str
    scene_count: int
    file_size_bytes: int
    created_at: str


# ========================================================
# 7. Publishing & Suite Contracts
# ========================================================

class PublishingSchedule(BaseModel):
    content_id: int
    platform: str
    scheduled_at: Optional[datetime] = None
    auto_publish: bool = False

class ContentSuiteRequest(BaseModel):
    brand: str # jade, doctorshield, jaguartransit
    topic: str
    key_benefits: List[str] = Field(default_factory=list)
    platforms: List[str] = Field(default=["linkedin", "instagram"])
    content_types: List[str] = Field(default=["post", "reel"])
    languages: List[str] = Field(default=["en"])
    generate_ab_variations: bool = True
    context_lessons: Optional[List[str]] = None

