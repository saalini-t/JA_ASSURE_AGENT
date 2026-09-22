export type Brand = 'jade' | 'doctorshield' | 'jaguartransit';

export type Platform = 'linkedin' | 'instagram' | 'facebook' | 'tiktok' | 'x' | 'blog' | 'reel';

export type ContentStatus = 
  | 'pending'
  | 'compliance_checked'
  | 'human_review'
  | 'approved'
  | 'rejected'
  | 'scheduled'
  | 'published';

export type ComplianceStatus = 'pending' | 'passed' | 'flagged' | 'failed';

export interface ContentQueueItem {
  id: number;
  brand: Brand;
  platform: Platform;
  content_type: string;
  topic: string;
  content_raw: string;
  variation: string;
  language: string;
  compliance_status: ComplianceStatus;
  status: ContentStatus;
  compliance_score: number;
  reason_tag?: string;
  notes?: string;
  metadata_json?: string;
  original_content_raw?: string;
  created_at: string;
  updated_at: string;
}

export interface ReviewDecisionItem {
  id: number;
  asset_type: string;
  asset_id: number;
  reviewer: string;
  decision: 'approve' | 'reject' | 'edit' | 'rewrite' | 'regenerate' | string;
  reason_tag?: string;
  notes?: string;
  original_content?: string;
  edited_content?: string;
  compliance_score?: number;
  previous_status: string;
  new_status: string;
  created_at: string;
}

export interface Competitor {
  id: number;
  name: string;
  url?: string;
  category: string;
  title: string;
  summary: string;
  detected_change?: string;
  actionable_recommendation?: string;
  relevance: number;
  source: string;
  source_type?: string;
  collected_at: string;
}

export interface CompetitorSnapshot {
  id: number;
  competitor_id: number;
  source_url?: string;
  source_type: string;
  title: string;
  summary: string;
  detected_change?: string;
  actionable_recommendation?: string;
  captured_at: string;
}

export interface CompetitorDigestEntry {
  competitor_id: number;
  competitor_name: string;
  category: string;
  source_url?: string;
  source_type: string;
  has_change: boolean;
  changed_fields: string[];
  previous_state: Record<string, any> | null;
  current_state: Record<string, any>;
  detected_at: string;
  why_it_matters?: string;
  suggested_action?: string;
  note?: string;
}

export interface Lead {
  id: number;
  name: string;
  company: string;
  industry: string;
  email?: string;
  location?: string;
  company_size?: string;
  fit_score: number;
  qualification_reason?: string;
  recommended_brand?: Brand;
  outreach_draft?: string;
  source?: string;
  source_type?: string;
  status: string;
  scoring_breakdown?: LeadScoringBreakdown | null;
  created_at: string;
}

export interface LeadScoringBreakdown {
  industry_fit: number;
  company_profile: number;
  geographic_relevance: number;
  product_relevance: number;
  potential_insurance_need: number;
  total_fit_score: number;
  industry_fit_reason?: string;
  company_profile_reason?: string;
  geographic_relevance_reason?: string;
  product_relevance_reason?: string;
  potential_insurance_need_reason?: string;
}

export interface LeadOutreach {
  id: number;
  lead_id: number;
  product: string;
  subject: string;
  body: string;
  original_body?: string;
  personalization_points: string[];
  source_evidence: string[];
  compliance_status: string; // pending, passed, flagged
  status: string; // pending, human_review, approved, rejected
  compliance_score: number;
  reason_tag?: string;
  notes?: string;
  send_status: string; // draft, sent, failed
  send_error?: string;
  sent_at?: string;
  created_at: string;
  updated_at: string;
}

export interface Feedback {
  id: number;
  content_id: number;
  reason_tag: string;
  notes: string;
  original_content: string;
  corrected_content?: string;
  created_at: string;
}

export interface LessonLearned {
  id: number;
  category: string;
  lesson: string;
  examples?: string;
  frequency: number;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface VideoScene {
  scene_number: number;
  duration_seconds: number;
  visual_description: string;
  voiceover: string;
  onscreen_text: string;
  transition?: string;
  compliance_disclaimer?: string;
}

export interface VideoScript {
  brand: string;
  title?: string;
  concept: string;
  hook?: string;
  target_duration_seconds: number;
  voiceover_tone: string;
  target_platform?: string;
  target_audience?: string;
  language?: string;
  scenes: VideoScene[];
  cta: string;
  disclaimer: string;
  media_status: string;

  // Voice Agent fields (populated by the standalone /content/voice endpoint --
  // one combined narration track for the whole script, teammate's voice_service.py)
  audio_url?: string;
  audio_filename?: string;
  audio_duration_seconds?: number;
  voice_provider?: string;
  voice_language?: string;
  voice_status?: string;

  // Phase 1 render result fields (populated by the backend's video_generation_service)
  job_id?: string;
  video_url?: string;
  video_duration_seconds?: number;
  scenes_generated?: number;
  image_source?: string; // ai_generated_openai | huggingface | branded_fallback_demo | mixed (...)
  render_status?: string; // completed | failed | skipped
  render_error?: string;

  // Phase 2 render result fields (per-scene voiceover + captions, integrated into the
  // actual FFmpeg assembly -- distinct from the standalone Voice Agent fields above)
  has_audio?: boolean;
  has_captions?: boolean;
  audio_source?: string; // e.g. gtts | openai_tts
  caption_file?: string;

  // Narration-duration budgeting fields
  narration_word_count?: number;
  narration_estimated_seconds?: number;
  narration_rewritten?: boolean;

  // Per-scene real-AI-vs-fallback image provenance -- NEVER label a fallback
  // scene as AI-generated in the UI; use is_real_ai/source/provider directly.
  scene_image_sources?: Array<{
    scene_number: number;
    source: string; // ai_generated_openai | huggingface | gemini | stable_diffusion_1_5 | branded_fallback_demo
    is_real_ai: boolean;
    provider: string;
    model?: string;
    provider_error?: string;
  }>;
  ai_generated_scene_count?: number;
  fallback_scene_count?: number;
}

export interface EngagementMetric {
  id: number;
  metric_name: string; // linkedin_likes, linkedin_comments
  brand?: string;
  platform?: string;
  metric_value: number;
  recorded_at: string;
}

export interface WorkerRunResult {
  processed: number;
  results: Array<{
    content_id: number;
    status: string;
    external_post_id?: string | null;
    error_info?: string | null;
    reason?: string;
  }>;
}

export interface VoiceGenerationResponse {
  status: string;
  audio_url: string;
  audio_filename: string;
  language: string;
  provider: string;
  duration_seconds?: number;
  voiceover_text: string;
  scene_count: number;
  file_size_bytes: number;
  created_at: string;
}

export interface GeneratedVariation {
  variation_label: string;
  content_text: string;
  headline?: string;
  hashtags: string[];
  cta?: string;
  media_prompt?: string;
}

export interface ClaimItem {
  claim_text: string;
  claim_type: string;
  risk_level: string;
  explanation?: string;
}

export interface ComplianceViolation {
  rule_id: string;
  category?: string;
  severity: string; // CRITICAL, HIGH, MEDIUM, LOW, warning, critical, info
  message: string;
  reason?: string;
  flagged_phrase?: string;
  matched_text?: string;
  suggested_fix?: string;
  recommendation?: string;
}

export interface ComplianceResult {
  passed: boolean;
  score: number;
  status?: string; // PASS, WARNING, BLOCKED, REQUIRES_HUMAN_REVIEW
  violations: ComplianceViolation[];
  warnings?: ComplianceViolation[];
  suggestions: string[];
  overall_feedback: string;
  disclaimers_required: string[];
  disclaimer_status?: string;
  claims_analyzed?: ClaimItem[];
  jurisdiction?: string;
  brand?: string;
  product?: string;
  platform?: string;
  language?: string;
  human_review_required?: boolean;
}

export interface PublishingRecord {
  id: number;
  content_id: number;
  platform: string;
  attempt: number;
  external_post_id?: string;
  status: string; // scheduled, publishing, published, failed, cancelled
  scheduled_at?: string;
  published_at?: string;
  engagement_metrics?: string; // JSON string -- parse for {source, likes, comments} or {source:"unavailable", reason}
  error_info?: string;
  created_at: string;
}

export interface DashboardSummary {
  total_content: number;
  pending_compliance: number;
  pending_human_review: number;
  compliance_approved: number;
  human_approved: number;
  approved: number;
  rejected: number;
  edited: number;
  published: number;
  approval_rate?: number;
  rejection_rate: number;
  average_compliance_score: number;
  total_leads: number;
  average_lead_score: number;
  total_lessons_learned: number;
  active_lessons_count?: number;
  total_feedback_count?: number;
  regeneration_count: number;
  brand_breakdown: Record<string, number>;
  platform_breakdown: Record<string, number>;
  language_breakdown: Record<string, number>;
  feedback_reason_frequency: Record<string, number>;
  compliance_score_distribution?: Record<string, number>;
  lead_score_distribution?: Record<string, number>;
  status_breakdown?: Record<string, number>;
}

export interface HealthCheckResponse {
  status: string;
  app_name: string;
  environment: string;
  database: string;
  database_type?: string;
  llm_provider?: string;
  llm_model?: string;
  llm_mode: string;
  supported_brands: string[];
}
