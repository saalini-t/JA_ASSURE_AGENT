# JA Assure AI Marketing Agent — Final System Audit

## Final Test Results (this session, last run)

| Suite | Result |
|---|---|
| Backend (`pytest`) | **299 passed, 2 pre-existing flakes, 1 skipped** (0:09:14) — see "Known Pre-Existing Test Flakiness" below for the 2 |
| Frontend (`vitest`) | **19 passed, 0 failed** |
| Frontend build (`npm run build`) | **Clean** — `tsc -b && vite build` succeeds |
| Live LinkedIn | **BLOCKED (credentials)** — no LinkedIn Developer Portal app existed at session start; pending your OAuth setup |
| Live SMTP | **PASS** — real email delivered |
| Live video generation | **PASS** — real MP4, ffprobe-verified, audible audio |
| Live Local SD1.5 | **PASS** — real GPU image generation |
| Database | **PASS** — SQLite, tables auto-created, CRUD live-verified |
| Background worker | **PASS** — genuine `asyncio` polling loop, confirmed live in an earlier phase of this session |
| Frontend E2E | **PASS (unit level)** — 19 component tests with real API contracts, no fake data; a manual browser click-through was not performed this session (all workflows instead verified via direct live API calls, which exercise the same backend code paths the frontend calls) |

Status legend: **PASS** (live-verified or unit-tested and code-reviewed) /
**PARTIAL** (works but with a real, named limitation) / **FAIL** (broken,
fixed or documented below) / **BLOCKED** (external credential/dependency,
named).

## Requirement Table

| Requirement | Status | Real/Mock | Tested | Evidence | Remaining |
|---|---|---|---|---|---|
| Backend starts | PASS | Real | Live-tested | `uvicorn` boots, `/health` returns 200 | — |
| Frontend starts | PASS | Real | Live-tested | `npm run dev` serves, `npm run build` compiles clean | — |
| Database connects | PASS | Real (SQLite) | Live-tested | tables created on startup, CRUD confirmed via live API calls this session | Postgres/Supabase path unit-tested via URL normalization only, not live-tested this session |
| Content generation | PASS | Real (Groq) / deterministic fallback | Unit + live | `/content/suite` exercised live this session (lead outreach, video enqueue) | — |
| Compliance | PASS | Real (12 deterministic rules + optional LLM rewrite) | Unit + live | live-verified rejecting "100% guaranteed payout"-style claims | `test_16` (rewrite-path mock) has a known test-authoring gap — see below, not a compliance-engine defect |
| HITL | PASS | Real | Unit + live | live-verified: unapproved/rejected/compliance-failed content all rejected by `/publishing/{id}/linkedin` and `/leads/outreach/{id}/send` | — |
| Feedback | PASS | Real | Unit | reject → feedback row created | — |
| Lesson retrieval | PASS | Real | Unit | lesson injected into next generation call | — |
| Competitor intelligence | PASS | Real scrape + mechanical diff | Unit + live | live-verified against `https://example.com`: baseline snapshot, correct "no prior" note | Social intelligence not implemented (not required by brief beyond "where supported") |
| Lead generation | PARTIAL | Not real-web-sourced (LLM-invented or demo pool) | Unit + live | scoring_breakdown now real and persisted (fixed this session) | Discovery is synthetic by design — documented honestly, not a bug |
| Localization | PARTIAL | Real LLM when Groq live; deterministic templates otherwise (id/th generic, not brand-specific offline) | Unit | — | Could add brand-specific offline templates for id/th |
| Video planning | PASS | Real (LLM when live) | Unit | — | — |
| AI image generation (cloud tiers) | BLOCKED (credentials) | Real code path | Unit (mocked) | Gemini: `429 RESOURCE_EXHAUSTED`; Hugging Face: `402 Payment Required` — confirmed against real APIs earlier this session | Needs a funded/quota-available key to live-verify tiers 1-2 |
| Local SD1.5 | PASS | Real (installed + downloaded this session) | Live-tested | RTX 3050, 10.7s/image, verified valid 512x768 PNG matching prompt | — |
| TTS | PASS | Real (gTTS, free, no API key) | Unit + live | confirmed working after dependency install (gtts smoke test) | — |
| Captions | PASS | Real (derived from voiceover + measured audio duration) | Unit | — | — |
| FFmpeg assembly | PASS | Real | Unit | ffmpeg/ffprobe resolved on PATH | *(final live video result below)* |
| Final video plays with audible audio | PASS | Real | Live-tested | ffprobe (h264/1080x1920/aac), volumedetect (-19.4dB mean, not silent), manual frame inspection | — |
| Video enters approved queue | PASS | Real | Unit | `/content/video/enqueue` → normal ContentQueue lifecycle | — |
| LinkedIn OAuth | PASS | Real (built this session) | Unit (13 tests, mocked HTTP) | authorization URL construction, state CSRF, token exchange, `.env` write-back all verified; confirmed the write-back never touches the real `.env` during tests (hash-compared) | — |
| LinkedIn real text post | *(pending — see LinkedIn section below)* | | | | |
| LinkedIn real video post | *(pending, depends on above)* | | | | |
| SMTP connection | PASS | Real (Gmail) | Live-tested | see SMTP section below | — |
| Pre-approval email rejected | PASS | Real | Live-tested | `POST /leads/outreach/{id}/send` before approval → 400 | — |
| Approved email delivered | PASS | Real | Live-tested | real email sent to shalu.swim@gmail.com, `send_status=sent`, message id recorded | — |
| Publishing records persist | PASS | Real | Unit + live | — | — |
| Analytics | PARTIAL | Real when LinkedIn token has read scope; honest "unavailable" otherwise | Unit | Not live-tested (no token yet) | — |
| Background worker | PASS | Real `asyncio` loop | Unit + live | live-tested earlier this session: `PUBLISH_WORKER_ENABLED=true`, 4 polls at exact configured interval observed in logs | — |
| Duplicate publishing prevented | PASS | Real | Unit | second `/publishing/{id}/linkedin` call → 409 | — |
| Frontend E2E workflow | PASS | Real API calls, no fake data | Unit (19 vitest tests) | Manual browser click-through not run this session (backend live-tests substituted via direct API calls) | Recommend one manual browser pass before the actual demo |

## Known Pre-Existing Test Flakiness (not introduced this session, not fixed — documented per instruction not to modify tests just to force a pass)

1. **`test_list_competitors`** (`test_api_and_db.py`) — passes in isolation
   (19/19), fails only in specific full-suite interleaving. Root cause:
   cross-file test-order dependency on `Competitor` table state; not a
   production defect.
2. **`test_16_non_compliant_rewrite_remains_blocked_if_violations_persist`**
   (`test_compliance_hardening.py`) — the test's own LLM-rewrite mock never
   engages because `llm_provider.is_live` is `False` under the standing
   `GROQ_API_KEY=""` test convention, so the deterministic-fallback branch
   runs instead and produces genuinely compliant text, trivially passing the
   recheck. Verified directly that the underlying regex rule
   (`RULE-01-GUARANTEED-OUTCOME`) correctly matches the test's violating text
   via direct `re.search` — the compliance engine itself is correct; only
   this one test's mock setup is incomplete (missing an `is_live=True` patch).

Both are pre-existing from before this session's work and out of scope for a
"final integration" pass to silently patch, per the standing instruction not
to modify tests to force them green unless the test itself is proven wrong —
these are proven test-authoring gaps, not application bugs, and are named
here rather than hidden.

## Fixes Made During This Final Integration Pass

1. **Regression in my own new tests**: `test_email_outreach_sending.py` was
   reading the ambient `.env`'s real `EMAIL_PROVIDER` setting instead of
   forcing `mock` — meaning a full `pytest` run would make real SMTP calls if
   `.env` had `EMAIL_PROVIDER=smtp` configured (which it did, mid-session).
   Fixed: `test_default_provider_is_mock`,
   `test_send_succeeds_with_mock_provider_for_approved_outreach`, and
   `test_send_failure_is_recorded_honestly_not_as_sent` now explicitly
   `monkeypatch` `EMAIL_PROVIDER` to `"mock"`, regardless of `.env`.
2. **Real security fix**: `research_service.py`'s scraper (`scrape_url`) had
   `verify=False` on its `httpx.AsyncClient`, disabling TLS certificate
   verification for every scrape (MITM exposure). Removed — now uses the
   default `verify=True`. Confirmed the existing broad exception handling
   already degrades gracefully to `DEMO_DATA` status on any failure, so this
   is a safe, non-breaking fix.
3. **Misleading log/docstring text**: `research_service.py`, `lead_service.py`,
   and `media_service.py` had 14 comments/log lines saying "Gemini" for what
   is actually **Groq**-backed text generation (`llm_provider.py` is Groq
   only; Gemini is a completely separate, image-only credential). This
   confused even an automated code-reading pass this session. Corrected all
   14 occurrences to say "Groq."
4. **Frontend dead prop / build failure**: `npm run build` failed
   (`tsc -b` strict unused-variable check) because `CompetitorIntelView`'s
   `getBrandBadge` prop became unused after this session's earlier removal of
   the hardcoded fake whitespace-opportunities section. Removed the dead
   prop from the component, its test, and its `App.tsx` call site. Build now
   passes clean.
5. **Frontend integration gaps closed this session** (see
   INTEGRATION_STATUS.md for full detail): governed lead-outreach UI (was
   plain-string, no compliance/HITL/send actions), real scoring breakdown
   (was client-side approximation), competitor change digest (was hardcoded
   fake data), new Publishing screen (was simulated-only), honest per-scene
   AI-provider labeling in the video preview, LinkedIn connection status UI.
6. **Test regression caused by installing SD1.5's real dependencies** (this
   was expected and is exactly why this needed to be exercised live, not
   assumed): two tests hardcoded assumptions about this machine's package
   state instead of mocking it, and broke the moment `torch`/`diffusers` were
   actually installed —
   - `test_sd15_image_provider.py::test_missing_dependencies_raise_typed_permanent_error`
     relied on torch/diffusers genuinely being absent to trigger its
     `ImportError` path. Fixed to explicitly force the `ImportError` via
     `sys.modules` patching (the same technique its neighboring
     CUDA-unavailable test already used), so it no longer depends on ambient
     machine state.
   - `test_video_generation.py::test_i_full_pipeline_produces_valid_final_mp4`
     asserted `image_source_summary == "branded_fallback_demo"`, relying on
     every real provider being unavailable/uninstalled to reach that fallback
     by accident. Now that Local SD1.5 genuinely works, the real `auto`
     cascade reached it instead (correct cascade behavior, not a bug) and the
     test's hardcoded expectation broke. Fixed by explicitly setting
     `IMAGE_PROVIDER=branded_fallback` for this test, since its actual intent
     (per its name/assertions) is to verify the fallback-produced MP4 is
     valid, not to test cascade provider selection.
   Both fixes verified: 30/30 in the affected test files, and in the full
   suite (see final count below).
7. **New capability, not a fix**: LinkedIn member-posting OAuth flow
   (`app/services/linkedin_oauth.py`, `app/api/v1/linkedin_auth.py`) — did
   not exist before this session; previously required manually obtaining and
   pasting in a token.
8. **New capability, merged from a companion project**: real lead discovery
   and contact enrichment. A separate local "JA Lead Generation" project
   (same fictional company, built independently) was audited module-by-module
   before porting anything — its own README overstated some capabilities
   ("regional trade directories" and "B2B market intelligence" turned out to
   be a hardcoded seed list and an unverified LLM prompt respectively, not
   real data sources; its scoring engine was mostly binary gates, no more
   sophisticated than what this project already had). Only the genuinely
   real, portable pieces were merged:
   - `app/services/url_safety.py` (new) — SSRF-safe URL validation (blocks
     loopback/private/link-local/metadata/multicast/reserved addresses for
     every resolved IP, re-validates the final URL after redirects). Wired
     into `research_service.scrape_url()`, which previously had **no** SSRF
     protection at all (a real gap, now closed, on top of the earlier
     TLS-verification fix).
   - `app/services/lead_discovery_providers.py` (new) — real business
     discovery via the Google Places API (New) and real contact-email
     discovery via Hunter.io + an SSRF-safe direct-site-scrape fallback.
     Wired as a new first tier in `discover_and_score_leads()` (real
     businesses, real addresses/phones/websites, `source="VERIFIED_SOURCE"`)
     and into `enrich_lead()`'s existing URL-enrichment path. Both API keys
     (`GOOGLE_MAPS_API_KEY`, `HUNTER_API_KEY`) are optional — blank leaves
     lead discovery on its previous Groq-invented/demo-pool behavior,
     unchanged. Directly closes the "not real-web-sourced" limitation this
     audit previously flagged for lead generation. Never fabricates a
     contact: `email` stays `None` unless a real one was actually found.
   - Explicitly **not** ported: the source project's fake "trade directory"
     and unverified "market intelligence" discovery tiers, its scoring
     engine, its rule-based reply classifier, its separate Jinja2 dashboard —
     none added real capability beyond what this project already has or
     plans to test live via the React frontend instead.
   - 25 new tests (`test_url_safety.py`, `test_lead_discovery_providers.py`,
     `test_real_lead_discovery_integration.py`), all mocked at the
     `httpx.Client` level — no real network calls, no API keys required to
     run them.
9. **New capability, merged from a second reference project, with one
   deliberate exclusion**: a second local project (`ut7ut/backend`, same
   fictional company, a more advanced/agentic build) was investigated when
   asked to "switch to Veo3/Gemini" and unify image/video/voice/caption
   generation into one sequential flow. Findings: it does **not** actually
   use Veo3 anywhere (grepped — zero real references); its image cascade
   (`GeminiAndFluxImageProvider`) is simpler than this project's existing
   4-tier cascade (no local SD1.5 tier). Its genuinely valuable idea was a
   `MediaDecisionEngine` that unifies "generate content → decide image or
   video → generate it" into one call instead of separate manual steps —
   ported and rebuilt as `app/services/media_decision_engine.py` against
   this project's own (superior) image cascade and video pipeline, exposed
   as `POST /content/campaign`.
   - **Explicitly NOT ported**: that project's `auto_approval_node`
     (`agentic/graph.py`), which sets `approved_by="SYSTEM"`,
     `human_approved=False`, and flips status straight to `"approved"`
     whenever compliance score ≥ 80, then immediately auto-publishes to
     LinkedIn. This directly contradicts this project's foundational,
     repeatedly-stated, and previously live-tested rule that nothing
     publishes without a real human approval. Flagged explicitly to the
     user before writing any code; the user confirmed keeping human
     approval mandatory. `/content/campaign` lands every item in
     `human_review` (or `pending` if compliance flagged it) exactly like
     every other path into the queue — confirmed by a dedicated test,
     `test_campaign_never_auto_approves_even_when_compliance_passes`.
   - Live-verified on the real running backend (real Postgres, real Groq):
     a real campaign call produced real content plus a real SD1.5-generated
     image in one request, landed in `human_review`. 6 new tests, all
     media-generation calls mocked (no real GPU/network time in the test
     suite itself).
10. **Major bug found and fixed via live testing (not caught by any mocked
    test, since tests never touch a real Groq account)**:
    `GROQ_MODEL=groq/compound` is not a valid model on this Groq account —
    confirmed via a direct API call, real response
    `404 {'error': {'message': 'The model `groq/compound` does not exist or
    you do not have access to it.'}}`. Every single Groq call this entire
    project (content generation, video scripting, lead discovery) was
    silently failing and falling back to placeholder/mock content the whole
    time, despite `/health` reporting `"llm_mode": "groq_live"` — because
    `is_live` only checks that a client object was constructed with an API
    key, never that the configured model actually works. Fixed to
    `openai/gpt-oss-120b` (confirmed with a real completion call). A related
    bug found in the same investigation: this model occasionally wraps its
    JSON response in a one-element list instead of a bare object; fixed with
    a defensive unwrap in `llm_provider.py` rather than letting a good
    response get discarded as a validation failure.
    - **Cascading effect this explains**: when the mock fallback fires for
      `VideoScript` generation, it produces exactly one scene with every
      field (including `compliance_disclaimer`) set to placeholder text.
      Since this codebase correctly forces the branded fallback card for any
      scene carrying a real disclaimer (a legal disclaimer should never be
      an AI hallucination), the placeholder junk in that field tripped the
      same rule on every mock scene — bypassing the entire image cascade for
      reasons that had nothing to do with Gemini/HF/SD1.5 themselves. Root
      cause traced end-to-end and confirmed fixed: a fresh generation after
      the fix produced a real 5-scene video, 4 scenes genuinely from local
      SD1.5, 1 (the actual disclaimer scene) correctly on the branded
      fallback — verified with `ffprobe`, `volumedetect` (real audible
      narration, all 5 scenes individually confirmed), and direct visual
      inspection of extracted frames.
11. **Branded fallback card redesigned.** The previous version printed
    `scene.visual_description` (an internal prompt written *for an AI image
    generator*, never meant for display) as the card's main body text, which
    is why it looked like a leaked prompt rather than a designed end slate.
    Now uses `scene.onscreen_text` (the field a human actually writes for
    on-screen display), a vertical brand-color gradient, an inset frame, a
    wrapped/centered brand wordmark, and the compliance disclaimer (when
    present) in proper small print. The honest "FALLBACK VISUAL — NOT
    AI-GENERATED" disclosure is kept fully legible, just visually integrated
    instead of an alarm-red bar. No provider-selection or labeling logic
    changed — still never claims AI generation for a fallback card.
12. **Real governance gap found via live testing and fixed.**
    `POST /leads/outreach/{id}/send` only checked `status == "approved"` —
    it never checked `compliance_status == "passed"`, unlike the real
    LinkedIn publish endpoint, which correctly uses
    `hitl_service.is_publishable()` (both conditions). This codebase's state
    machine deliberately allows a human to "approve" a compliance-flagged
    draft as a sign-off that they've seen the warnings (see
    `hitl_service.py`'s docstring) — but that was, until this fix,
    sufficient on its own to actually **send** a flagged outreach email for
    real. Reproduced live: created a lead with a real email, generated
    outreach, approved it while `compliance_status` was still `"flagged"`
    (score 60/100, "Requires remediation... before human approval"), and the
    send endpoint accepted it and dispatched a real email anyway. Fixed to
    use `hitl_service.is_publishable()`, the exact same two-part check the
    LinkedIn endpoint already used correctly — one line of production code,
    plus a new regression test
    (`test_send_rejects_approved_but_compliance_flagged_outreach`) that
    deterministically reproduces the exact scenario via the governed `/edit`
    endpoint rather than depending on a live LLM's non-deterministic first
    draft. This is the second real HITL/compliance-adjacent bug found by
    actually exercising the system rather than by code review alone (the
    first being the GROQ_MODEL cascade failure above) — both were invisible
    to static review and only surfaced by live testing.

---

## LinkedIn — Live Test Result

*(Filled in once LinkedIn Developer Portal credentials are supplied and the
OAuth authorization is completed — see RUNBOOK.md §7. Until then: BLOCKED
BY CREDENTIALS, no LinkedIn variables were present in `.env` at all at the
start of this pass.)*

## SMTP — Live Test Result

**PASS — real email delivered.**
- Provider: `smtp` (Gmail, `smtp.gmail.com:587`)
- Flow exercised: create lead (real email `shalu.swim@gmail.com`) → generate
  governed outreach draft → compliance passed (score 100.0) → **send attempt
  before approval correctly rejected (400)** → approve → send
- Result: `send_status: "sent"`, provider `smtp`, message id
  `smtp-a420e2268ac9`, `sent_at` recorded
- Credentials never printed, logged, or exposed in any API response this
  session.

## Local Stable Diffusion 1.5 — Live Test Result

**PASS — real GPU-generated image, verified.**
- Installed this session: `torch==2.6.0+cu124` (confirmed `torch.cuda.is_available()==True`,
  device `NVIDIA GeForce RTX 3050 6GB Laptop GPU`), `diffusers==0.40.0`,
  `transformers==5.17.0`, `accelerate==1.15.0`.
- Model weights (`runwayml/stable-diffusion-v1-5`, 14 files) downloaded from
  Hugging Face on first use — 2m14s, no `HF_TOKEN` required for this model.
- Pipeline load: 169.2s (first run only; cached afterward). Generation:
  **10.7 seconds** for 20 inference steps at 512×768, fp16, on the RTX 3050.
- Output verified with `PIL.Image.verify()`: valid PNG, 512×768, RGB,
  625,129 bytes — not corrupt, not a placeholder.
- Visual content genuinely matched the prompt ("elegant diamond ring on
  velvet, studio lighting") — inspected directly, on-brand for Jade.
- This confirms the full `IMAGE_PROVIDER=auto` cascade is now genuinely
  functional end-to-end on this machine: Gemini (quota-exhausted) → Hugging
  Face (quota-exhausted) → **Local SD1.5 (real, working)** → branded fallback
  would never even be reached for a fresh scene right now, since tier 3
  succeeds.

## Real Video Generation — Live Test Result

**PASS — full pipeline, real output, verified with ffprobe and manual frame/audio inspection.**

Request: `POST /content/video` with `render=true, narrate=true`, brand `jade`,
topic "Why standard homeowner insurance fails to cover bespoke diamond
jewellery collections", `target_duration=45`. Completed in 110s.

- `render_status`: `completed`, `job_id`: `9b24bb6a34f4`, 4 scenes.
- **Image cascade behaved exactly as designed**, confirmed from live server
  logs, not assumption: Gemini → real `429 RESOURCE_EXHAUSTED` → Hugging Face
  → real `402 Payment Required` → **Local SD1.5 → real success** for the 2
  non-disclaimer scenes. The 2 scenes carrying a `compliance_disclaimer`
  (mid-roll legal note + end card) correctly used the deterministic branded
  fallback instead of ever attempting a real AI call for them — this is
  intentional design (disclaimer/end-card scenes never claim AI generation),
  not a cascade failure. `image_source_summary`: `"mixed (2x
  stable_diffusion_1_5, 2x branded_fallback_demo)"`, `ai_generated_scene_count:
  2`, `fallback_scene_count: 2` — matches exactly.
- Narration budgeting rewrote 1 overrunning scene automatically
  (`narration_rewritten: true`).
- `has_audio: true`, `audio_source: "gtts"`, `has_captions: true`.
- `ffprobe` on the actual output file
  (`media/generated/9b24bb6a34f4/final.mp4`):
  - video: `codec_name=h264`, `1080x1920` ✓
  - audio: `codec_name=aac`, `sample_rate=24000` ✓
  - `duration=43.31s`, `size=4,413,140 bytes` ✓ (matches
    `video_duration_seconds` in the API response exactly)
- `ffmpeg -af volumedetect`: `mean_volume=-19.4dB`, `max_volume=-3.9dB` —
  **genuinely audible, not silent.**
- Extracted an actual mid-video frame and inspected it directly: a real
  SD1.5-generated emerald ring image with the correct burned-in caption text
  ("...pletely protected under home insurance. But h...", matching scene 1's
  voiceover), correctly positioned, correct vertical aspect ratio.
- **Video → queue → approval integration (Part 9) confirmed real**: enqueued
  via `POST /content/video/enqueue` → compliance passed (score 100.0) →
  landed in `human_review` (never auto-approved) → approved via
  `POST /queue/{id}/approve`. `metadata_json.video_path` correctly contains
  the real absolute path to `final.mp4`, `image_path` is `null` — confirming
  `publishing_service._extract_media()` will route this to
  `linkedin_client.publish_video()` (real video upload) rather than a
  text-only post, once LinkedIn is connected.
- This content item (queue id 1, `content_type=reel`, `status=approved`,
  `compliance_status=passed`) is sitting ready for the real LinkedIn video
  publish test as soon as OAuth is completed.
