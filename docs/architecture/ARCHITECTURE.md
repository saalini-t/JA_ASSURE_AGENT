# JA Assure AI Marketing Agent — System Architecture

## 1. Executive Summary

The JA Assure AI Marketing Agent is a governed, end-to-end marketing automation
platform for a multi-brand insurance company (Jade, DoctorShield, Jaguar
Transit) operating across Southeast Asia. It connects competitive research,
generative copywriting, real AI video production, regulatory compliance
checking, closed-loop human-in-the-loop (HITL) learning, lead discovery and
qualification, and real multi-channel publishing (LinkedIn, email) into one
auditable pipeline — not a collection of independent demo screens.

The defining architectural principle is **honesty over appearance**: every
provider tier reports whether it actually ran, every fallback is labeled as a
fallback, and every governance gate is enforced server-side in one place, so
it cannot be bypassed by a different code path or a frontend that "forgets"
to check.

---

## 2. End-to-End Pipeline

```
┌────────────────┐
│ Research /      │  Real SSRF-safe scraping of a supplied URL, or an LLM-
│ Competitor      │  assisted "AI_ANALYSIS" pass, topped up with a small demo
│ Intelligence    │  competitor set. Every scrape upserts a Competitor row and
│                 │  appends an immutable CompetitorSnapshot -- the "digest"
└───────┬─────────┘  endpoint is a mechanical field-diff between the two most
        │             recent snapshots, never an LLM guess at what changed.
        ▼
┌────────────────┐
│ Content         │  Brand-voice-aware generation (Groq LLM when configured,
│ Generation      │  deterministic templates otherwise) across platforms
│                 │  (LinkedIn/Instagram/X/blog/carousel), with A/B variants
└───────┬─────────┘  and active Lessons Learned injected into every prompt.
        ▼
┌────────────────┐
│ Repurposing +   │  One idea -> many formats; content localized into English,
│ Localization    │  Malay, Bahasa Indonesia, Thai, Chinese (real LLM adaptation
│                 │  when live, brand-aware deterministic templates otherwise).
└───────┬─────────┘
        ▼
┌────────────────┐
│ Compliance Gate │  12 deterministic regex/heuristic rules (prohibited
│                 │  superlatives, unverified guarantees, missing statutory
│                 │  disclaimers, etc.) producing a 0-100 score + reasons.
└───────┬─────────┘  An LLM-assisted rewrite path can clean up violations,
        │             always re-checked afterward -- never trusted blind.
        ▼
┌────────────────┐
│ Human Review    │  hitl_service.py is the SINGLE source of truth for every
│ (HITL)          │  legal state transition (pending -> human_review ->
│                 │  approved/rejected, edit always returns to human_review).
└───────┬─────────┘  Used identically by ContentQueue and LeadOutreach.
        │
        ├─────────────────────────────┬───────────────────────────────┐
        ▼                              ▼                               ▼
┌────────────────┐          ┌────────────────────┐          ┌──────────────────┐
│ Video Generation │          │ Real LinkedIn        │          │ Feedback / Lessons │
│ (optional)       │          │ Publishing            │          │                    │
│                  │          │                       │          │ Every reject/edit  │
│ scenes -> 4-tier │          │ hitl_service gate ->  │          │ synthesizes a       │
│ image cascade -> │          │ idempotency check ->  │          │ structured Lesson,  │
│ gTTS narration   │          │ LinkedIn REST v2 ->   │          │ retrieved by topic/ │
│ -> captions ->   │          │ retry (transient only)│          │ brand and injected  │
│ FFmpeg -> real   │          │ -> immutable          │          │ into future prompts.│
│ MP4              │          │ PublishingRecord      │          │                    │
└────────┬─────────┘          └──────────┬────────────┘          └────────────────────┘
         │                                │
         │  video enters the same          │  optional background worker polls
         │  ContentQueue/HITL/compliance    │  for approved+passed content on an
         │  lifecycle as any other asset    │  interval -- disabled by default,
         └─────────────────────────────────┘  same gated path as manual trigger

┌────────────────────┐     ┌──────────────────────┐     ┌───────────────────┐     ┌──────────────┐
│ Lead Discovery       │────▶│ 5-Factor Scoring       │────▶│ Governed Outreach   │────▶│ Real SMTP     │
│                      │     │                        │     │                     │     │ Send          │
│ Real: Google Places   │     │ Deterministic, brand-  │     │ Draft -> compliance │     │               │
│ API + Hunter.io/scrape│     │ specific weighted       │     │ -> human_review ->  │     │ Gated on      │
│ contact enrichment.   │     │ rubric, persisted per   │     │ approve/reject/edit │     │ status==      │
│ Fallback: Groq-       │     │ lead as scoring_       │     │ -> send (only when  │     │ approved AND  │
│ assisted invented     │     │ breakdown_json, never   │     │ approved AND a real │     │ a real email   │
│ profiles or demo pool.│     │ approximated client-side│     │ email exists)        │     │ exists.        │
└────────────────────┘     └──────────────────────┘     └───────────────────┘     └──────────────┘
```

Every arrow terminates in a persisted, queryable database row — nothing in
this pipeline is fire-and-forget or held only in memory.

---

## 3. Database Schema (SQLAlchemy models, `app/models/entities.py`)

| Table | Purpose | Notable fields |
|---|---|---|
| `content_queue` | Every piece of generated marketing content, any platform/language/format | `status` (pending→human_review→approved→scheduled→published, or rejected), `compliance_status`, `compliance_score`, `metadata_json` (carries `video_path`/`image_path` for media assets) |
| `review_decisions` | Immutable audit trail of every HITL action | `decision`, `previous_status`, `new_status`, `original_content`, `edited_content` — one row per action, never overwritten |
| `competitors` | Current known state per tracked competitor | `source_type` (`VERIFIED_SOURCE`/`AI_ANALYSIS`/`DEMO_DATA`) |
| `competitor_snapshots` | Append-only history, one row per research run | Used exclusively for mechanical change-detection between the two most recent rows |
| `leads` | B2B prospects | `fit_score`, `scoring_breakdown_json` (real 5-factor persisted breakdown), `source`/`source_type`, `email` (only ever real or `None`) |
| `lead_outreach` | Governed outreach drafts, separate from the legacy ungoverned `Lead.outreach_draft` string field | `compliance_status`, `status` (HITL state machine, same primitives as `content_queue`), `send_status`/`send_error`/`sent_at` |
| `feedback` | One row per human rejection/edit | Feeds `lessons_learned` synthesis |
| `lessons_learned` | Generalized, brand-scoped rules extracted from feedback | `category`, `frequency`, `active` — retrieved by topic/brand relevance and injected into future generation prompts |
| `publishing_records` | One immutable row per publish **attempt** (not per content item) | `platform`, `attempt`, `external_post_id`, `status`, `engagement_metrics` (real data or an honest `{"source":"unavailable"}` payload) |
| `analytics` | Real per-post engagement metrics only | Only ever written by a genuine successful LinkedIn API response |

Tables are created automatically on backend startup (`Base.metadata.create_all`)
against whatever `DATABASE_URL` points to. **This does not alter existing
tables when a model gains a new column** — a real gap encountered and fixed
during this project's development (see `docs/FINAL_SYSTEM_AUDIT.md`); a
production deployment with an existing database needs an explicit `ALTER
TABLE` (or a fresh database) after a schema change, same as any SQLAlchemy
project without a migration tool like Alembic.

---

## 4. Compliance Engine

Deterministic, rule-based, and inspectable — not a black-box LLM judgment call
for the actual pass/fail decision:

- 12 registered rules (`GET /compliance/rules`) covering prohibited absolute
  guarantees, unverified savings/superlative claims, missing statutory
  intermediary disclaimers, unauthorized financial/medical/legal advice, and
  more — each with a severity (`CRITICAL`/`HIGH`/`MEDIUM`/`LOW`).
- Produces a 0–100 score, a pass/fail/flagged status, and human-readable
  reasons per violation.
- An **optional** LLM-assisted rewrite path (used only when Groq is
  configured) can propose a cleaned-up version — the rewritten text is always
  re-run through the same deterministic gate before being trusted, never
  accepted purely on the LLM's say-so.
- The exact same gate function (`hitl_service.is_publishable`) is the single
  place that decides whether *any* content — a text post, a video, an
  outreach email — is allowed to leave the system. There is no second,
  differently-gated code path anywhere.

---

## 5. Image Provider Cascade

`ImageMotionProvider` (`app/services/video_providers.py`) tries, in order,
stopping at the first real success:

1. **Gemini** (`GeminiImageProvider`) — `models/gemini-2.5-flash-image` via the
   `google-genai` SDK.
2. **Hugging Face** (`HuggingFaceImageProvider`) — FLUX.1-dev via Inference
   Providers.
3. **Local Stable Diffusion 1.5** (`LocalSD15ImageProvider`) — lazy-loaded
   `diffusers`/`torch`, CUDA-accelerated when available, low-VRAM mode
   (attention slicing + sequential CPU offload) for constrained GPUs. Never
   imported or loaded at application startup.
4. **Branded fallback** (`BrandedFallbackProvider`) — a deterministic,
   PIL-rendered card. Always succeeds, always honestly labeled.

Setting `IMAGE_PROVIDER` to one specific value bypasses the cascade entirely
and forces exactly that provider (used for a disclaimer/end-card scene, which
always uses the branded fallback regardless of cascade mode, since a legal
disclaimer card should never be an AI hallucination). Every scene's result
carries `source`, `provider`, `model`, `is_real_ai`, and `provider_error` —
the frontend renders these directly rather than inferring AI-ness from
whether *any* provider was configured.

---

## 6. Video Generation Pipeline

`video_generation_service.py` orchestrates, per video:

1. Deterministic scene-duration normalization against the requested total.
2. Scene validation (structural, not AI).
3. Narration-duration budgeting — estimates spoken length from word count at
   a configurable words-per-minute, rewrites overrunning scenes.
4. Per scene: image generation via the cascade above.
5. Per scene (if narrated): gTTS voiceover; a scene's *measured* audio
   duration (via `ffprobe`, never assumed) becomes authoritative.
6. Captions: SRT cues derived directly from the scene's own voiceover text and
   its measured audio duration — no speech-to-text involved. Burned in
   per-scene via FFmpeg `drawtext`; a full downloadable `.srt` is also
   produced.
7. Per-scene FFmpeg render: cover-crop + `zoompan` pan/zoom motion (rotates
   deterministically through zoom-in/pan-left/pan-right/zoom-out, never
   LLM-chosen), `libx264`, `yuv420p`, 1080×1920, 30fps; `aac` audio when
   narrated.
8. Concatenation via FFmpeg's `concat` demuxer (stream-copy, no re-encode).
9. Output validation via `ffprobe`: confirms a real video stream, a real audio
   stream when narrated, non-zero duration and file size — raises rather than
   silently reporting success on a corrupt or empty file.

The result includes `ai_generated_scene_count` and `fallback_scene_count` so a
"mixed" result (some real AI scenes, some fallback) is never misreported as
either fully AI or fully fallback.

---

## 7. Real Publishing (LinkedIn)

- `linkedin_client.py` — stateless REST calls only (`httpx`, no SDK). Author
  URN resolution tries the member's own identity first (`/v2/userinfo`, then
  `/v2/me`), falling back to `LINKEDIN_ORGANIZATION_ID` only if both fail and
  an org ID happens to be configured — **member posting is the default
  behavior**, not something bolted on afterward.
- `linkedin_oauth.py` / `api/v1/linkedin_auth.py` — in-app OAuth 2.0
  authorization-code flow requesting exactly `openid profile w_member_social`
  (never an organization/company-page scope). CSRF-protected via a one-time
  `state` token. The resulting access token is written to `backend/.env`
  (best-effort, in addition to an in-memory update) and never returned in any
  API response or logged.
- `publishing_service.py` — the **only** caller of `linkedin_client.py`.
  Enforces the HITL/compliance gate before ever reaching LinkedIn, checks
  idempotency (refuses a duplicate publish, `409`), retries transient
  failures (timeout/5xx/rate-limit) with bounded backoff, never retries
  permanent failures (missing token, invalid payload). Every attempt gets its
  own immutable `PublishingRecord` row.
- `publishing_worker.py` — an optional `asyncio` background loop
  (`PUBLISH_WORKER_ENABLED`, default `false`) that finds approved +
  compliance-passed content and publishes it through the *exact same*
  `publishing_service.publish_to_linkedin()` call a manual trigger uses —
  there is no separate, less-governed automatic path.

---

## 8. Real Email Outreach

- `email_provider.py` — a small `EmailProvider` abstraction: `MockEmailProvider`
  (default, logs and returns a labeled mock result, touches no network) and
  `SMTPProvider` (stdlib `smtplib`, works with Gmail/SendGrid/Resend/any
  standard SMTP host).
- The send endpoint (`POST /leads/outreach/{id}/send`) is the **only** path
  from a drafted outreach to an actual email. It hard-rejects anything not
  `status=='approved'`, and hard-rejects if the lead has no real email on
  file — outreach never fabricates a recipient to send to.
- Automated tests force `EMAIL_PROVIDER=mock` explicitly regardless of the
  developer's local `.env`, so `pytest` can never make a real SMTP connection
  even if a machine has real credentials configured for manual testing.

---

## 9. Real Lead Discovery

- `lead_discovery_providers.py` — real business discovery via the Google
  Places API (New) `searchText` endpoint (genuine name, address, phone,
  website — never a fabricated contact), and real contact-email discovery via
  Hunter.io (if configured) falling back to an SSRF-safe direct homepage
  scrape (regex extraction with noise/system-address filtering).
- `url_safety.py` — a self-contained SSRF guard (blocks loopback, RFC1918
  private ranges, link-local/cloud-metadata addresses, multicast, and
  IANA-reserved ranges for every resolved IP, not just the first; re-validates
  the final URL after any redirect chain) used by both the lead-contact
  scraper and the competitor-intelligence scraper.
- When no `GOOGLE_MAPS_API_KEY` is configured, discovery falls through to a
  Groq-assisted "invent plausible prospect profiles" pass (explicitly
  instructed never to fabricate contact details) or a small hardcoded demo
  pool — both clearly tagged `AI_GENERATED_PROSPECT` / `DEMO_DATA`, distinct
  from the real tier's `VERIFIED_SOURCE` tag.
- The 5-factor fit score (industry, company profile, geography, product
  match, insurance need) is computed identically regardless of which
  discovery tier found the lead, and persisted as a real
  `scoring_breakdown_json` — the frontend renders this real breakdown
  directly rather than approximating one from the total score.

---

## 10. Security & Governance Principles

- **No hardcoded secrets** — every credential loads through environment
  variables (`app/config.py`, `pydantic-settings`); `.env` is gitignored,
  `.env.example` carries no real values.
- **SSRF protection** on both outbound scrapers (competitor research, lead
  contact enrichment) — arbitrary user- or AI-supplied URLs are validated
  against private/loopback/link-local/metadata address ranges before ever
  being fetched.
- **Graceful, honest degradation** — every optional integration (LLM, image
  providers, LinkedIn, email, lead data) has a safe, clearly-labeled fallback;
  the system is fully testable and demoable with zero API keys configured.
- **Mandatory human-in-the-loop** — enforced by one shared state-machine
  service (`hitl_service.py`), not duplicated/reimplemented per feature.
- **Immutable audit trails** — every HITL decision and every publish attempt
  is its own row, never overwritten, so the full history of any content item
  is always reconstructable.
- **Idempotency where it matters** — a content item cannot be published to
  LinkedIn twice; the check runs before the HITL gate specifically so a
  genuine duplicate returns a clear `409` rather than a confusing "not
  approved" error (since a successful publish flips status away from
  "approved").
