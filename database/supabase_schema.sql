-- ==============================================================================
-- JA ASSURE AI MARKETING AGENT — SUPABASE POSTGRESQL PRODUCTION SCHEMA
-- ==============================================================================
-- Multi-brand InsurTech platform (Jade, DoctorShield, Jaguar Transit).
-- Paste and execute directly in the Supabase SQL Editor.
-- Idempotent schema: safe to run on fresh or existing databases.
-- ==============================================================================

-- 1. CONTENT QUEUE (Core Content Generation & Human Review Staging)
CREATE TABLE IF NOT EXISTS content_queue (
    id SERIAL PRIMARY KEY,
    brand VARCHAR(50) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    content_type VARCHAR(50) NOT NULL DEFAULT 'post',
    topic VARCHAR(255) NOT NULL,
    content_raw TEXT NOT NULL,
    variation VARCHAR(50) NOT NULL DEFAULT 'A',
    language VARCHAR(10) NOT NULL DEFAULT 'en',
    compliance_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    compliance_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    reason_tag VARCHAR(100),
    notes TEXT,
    metadata_json TEXT,
    original_content_raw TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_content_brand CHECK (brand IN ('jade', 'doctorshield', 'jaguartransit')),
    CONSTRAINT chk_content_status CHECK (status IN ('pending', 'compliance_checked', 'human_review', 'approved', 'rejected', 'scheduled', 'published')),
    CONSTRAINT chk_compliance_status CHECK (compliance_status IN ('pending', 'passed', 'flagged', 'failed'))
);

CREATE INDEX IF NOT EXISTS ix_content_queue_id ON content_queue(id);
CREATE INDEX IF NOT EXISTS ix_content_queue_brand ON content_queue(brand);
CREATE INDEX IF NOT EXISTS ix_content_queue_platform ON content_queue(platform);
CREATE INDEX IF NOT EXISTS ix_content_queue_status ON content_queue(status);
CREATE INDEX IF NOT EXISTS ix_content_queue_compliance_status ON content_queue(compliance_status);
CREATE INDEX IF NOT EXISTS ix_content_brand_platform ON content_queue(brand, platform);
CREATE INDEX IF NOT EXISTS ix_content_status_compliance ON content_queue(status, compliance_status);

-- 2. COMPETITOR INTELLIGENCE & OBSERVED CLAIMS
CREATE TABLE IF NOT EXISTS competitors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    url VARCHAR(255),
    category VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    summary TEXT NOT NULL,
    detected_change TEXT,
    actionable_recommendation TEXT,
    relevance DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    source VARCHAR(100) NOT NULL DEFAULT 'public_web',
    collected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_competitors_id ON competitors(id);
CREATE INDEX IF NOT EXISTS ix_competitors_name ON competitors(name);
CREATE INDEX IF NOT EXISTS ix_competitors_category ON competitors(category);

-- 3. LEAD PROSPECTING & 5-FACTOR QUALIFICATION
CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    company VARCHAR(150) NOT NULL,
    industry VARCHAR(100) NOT NULL,
    email VARCHAR(150),
    location VARCHAR(100),
    company_size VARCHAR(50),
    fit_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    qualification_reason TEXT,
    recommended_brand VARCHAR(50),
    outreach_draft TEXT,
    source VARCHAR(100) DEFAULT 'prospecting',
    status VARCHAR(50) NOT NULL DEFAULT 'new',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_lead_status CHECK (status IN ('new', 'contacted', 'qualified', 'converted', 'archived'))
);

CREATE INDEX IF NOT EXISTS ix_leads_id ON leads(id);
CREATE INDEX IF NOT EXISTS ix_leads_company ON leads(company);
CREATE INDEX IF NOT EXISTS ix_leads_industry ON leads(industry);
CREATE INDEX IF NOT EXISTS ix_leads_status ON leads(status);

-- 4. HUMAN FEEDBACK & EDITORIAL AUDIT TRAIL
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    content_id INTEGER NOT NULL REFERENCES content_queue(id) ON DELETE CASCADE,
    reason_tag VARCHAR(100) NOT NULL,
    notes TEXT NOT NULL,
    original_content TEXT NOT NULL,
    corrected_content TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_feedback_id ON feedback(id);
CREATE INDEX IF NOT EXISTS ix_feedback_content_id ON feedback(content_id);
CREATE INDEX IF NOT EXISTS ix_feedback_reason_tag ON feedback(reason_tag);

-- 5. CLOSED-LOOP LESSONS LEARNED (Persistent AI Memory)
CREATE TABLE IF NOT EXISTS lessons_learned (
    id SERIAL PRIMARY KEY,
    category VARCHAR(100) NOT NULL,
    lesson TEXT NOT NULL,
    examples TEXT,
    frequency INTEGER NOT NULL DEFAULT 1,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_lessons_learned_id ON lessons_learned(id);
CREATE INDEX IF NOT EXISTS ix_lessons_learned_category ON lessons_learned(category);
CREATE INDEX IF NOT EXISTS ix_lessons_learned_active ON lessons_learned(active);

-- 6. SYSTEM TELEMETRY & ANALYTICS METRICS
CREATE TABLE IF NOT EXISTS analytics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    brand VARCHAR(50),
    platform VARCHAR(50),
    metric_value DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    metadata_json TEXT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_analytics_id ON analytics(id);
CREATE INDEX IF NOT EXISTS ix_analytics_metric_name ON analytics(metric_name);
CREATE INDEX IF NOT EXISTS ix_analytics_brand ON analytics(brand);
CREATE INDEX IF NOT EXISTS ix_analytics_platform ON analytics(platform);

-- 7. PUBLISHING RECORDS (Human-Controlled Simulated Dispatch Staging)
CREATE TABLE IF NOT EXISTS publishing_records (
    id SERIAL PRIMARY KEY,
    content_id INTEGER NOT NULL REFERENCES content_queue(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    external_post_id VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'scheduled',
    scheduled_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    engagement_metrics TEXT,
    error_info TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_publishing_status CHECK (status IN ('scheduled', 'publishing', 'published', 'failed', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS ix_publishing_records_id ON publishing_records(id);
CREATE INDEX IF NOT EXISTS ix_publishing_records_content_id ON publishing_records(content_id);
CREATE INDEX IF NOT EXISTS ix_publishing_records_platform ON publishing_records(platform);
CREATE INDEX IF NOT EXISTS ix_publishing_records_status ON publishing_records(status);

-- Idempotent migration for databases provisioned before original_content_raw existed.
ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS original_content_raw TEXT;

-- 8. REVIEW DECISIONS (HITL Audit Trail — Human-in-the-Loop governance log)
-- Deliberately polymorphic (asset_type + asset_id, no FK) so the same governance boundary
-- can later cover Lead/Outreach drafts and Competitor Recommendations, not just content_queue.
CREATE TABLE IF NOT EXISTS review_decisions (
    id SERIAL PRIMARY KEY,
    asset_type VARCHAR(50) NOT NULL DEFAULT 'content_queue',
    asset_id INTEGER NOT NULL,
    reviewer VARCHAR(100) NOT NULL DEFAULT 'compliance_officer',
    decision VARCHAR(50) NOT NULL,
    reason_tag VARCHAR(100),
    notes TEXT,
    original_content TEXT,
    edited_content TEXT,
    compliance_score DOUBLE PRECISION,
    previous_status VARCHAR(50) NOT NULL,
    new_status VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_review_decision CHECK (decision IN ('approve', 'reject', 'edit', 'rewrite', 'regenerate'))
);

CREATE INDEX IF NOT EXISTS ix_review_decisions_id ON review_decisions(id);
CREATE INDEX IF NOT EXISTS ix_review_decisions_asset_type ON review_decisions(asset_type);
CREATE INDEX IF NOT EXISTS ix_review_decisions_asset_id ON review_decisions(asset_id);
CREATE INDEX IF NOT EXISTS ix_review_decisions_decision ON review_decisions(decision);
CREATE INDEX IF NOT EXISTS ix_review_decisions_created_at ON review_decisions(created_at);
CREATE INDEX IF NOT EXISTS ix_review_decisions_asset ON review_decisions(asset_type, asset_id);

-- Automatic updated_at trigger helper
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS trg_content_queue_updated_at ON content_queue;
CREATE TRIGGER trg_content_queue_updated_at
    BEFORE UPDATE ON content_queue
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_lessons_learned_updated_at ON lessons_learned;
CREATE TRIGGER trg_lessons_learned_updated_at
    BEFORE UPDATE ON lessons_learned
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();




ALTER TABLE content_queue
ADD COLUMN IF NOT EXISTS original_content_raw TEXT;

CREATE TABLE IF NOT EXISTS review_decisions (
    id SERIAL PRIMARY KEY,
    asset_type VARCHAR(50) NOT NULL,
    asset_id INTEGER NOT NULL,
    reviewer VARCHAR(255),
    decision VARCHAR(50) NOT NULL,
    reason_tag VARCHAR(100),
    notes TEXT,
    original_content TEXT,
    edited_content TEXT,
    compliance_score FLOAT,
    previous_status VARCHAR(50),
    new_status VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);