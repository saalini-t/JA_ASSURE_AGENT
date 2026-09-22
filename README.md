# 🛡️ JA Assure AI Marketing Agent

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-v4-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Groq](https://img.shields.io/badge/Groq-LLM_Inference-F55036.svg?logo=groq&logoColor=white)](https://groq.com/)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Real_OAuth_Publishing-0A66C2.svg?logo=linkedin&logoColor=white)](https://developer.linkedin.com/)
[![Tests](https://img.shields.io/badge/Backend_Tests-324_passed-success.svg)](docs/TESTING_GUIDE.md)
[![Tests](https://img.shields.io/badge/Frontend_Tests-19_passed-success.svg)](docs/TESTING_GUIDE.md)

> **An autonomous, multi-brand agentic marketing, regulatory compliance, video production, and lead intelligence platform for JA Assure across Southeast Asia — with real AI image/video generation, real LinkedIn publishing, and real email outreach, all gated behind mandatory human approval.**

---

### 🌟 Core Differentiator

> **"Human feedback becomes persistent lessons that influence future AI generations — and nothing this system reports as done was ever left to look done."**
>
> Every human rejection or inline edit automatically synthesizes a structured, persistent **Lesson Learned**, dynamically retrieved and injected into future prompts. Every "AI-generated" label is backed by a real API call that actually happened; every fallback is honestly named as a fallback; every "published" or "sent" status reflects an outcome a real external provider actually confirmed. This isn't a demo that fakes success — it's a governed pipeline that fails loudly and honestly when something is unavailable, and works for real when it is.

---

## 📑 Table of Contents
1. [Problem Statement](#-1-problem-statement)
2. [What This System Actually Does](#-2-what-this-system-actually-does)
3. [Key Features](#-3-key-features)
4. [System Architecture](#-4-system-architecture)
5. [Technology Stack](#-5-technology-stack)
6. [Repository Structure](#-6-repository-structure)
7. [Quick Start](#-7-quick-start)
8. [Environment Variables](#-8-environment-variables)
9. [Real vs. Fallback — Read This Before a Demo](#-9-real-vs-fallback--read-this-before-a-demo)
10. [Automated Tests](#-10-automated-tests)
11. [Documentation Index](#-11-documentation-index)
12. [Governance Guardrails](#-12-governance-guardrails)
13. [Repository](#-13-repository)

---

## 🎯 1. Problem Statement

JA Assure manages specialized, high-value insurance portfolios across Singapore, Malaysia, Thailand, and Indonesia under three brands:
- **Jade** — high-net-worth bespoke luxury jewellery, watch, and private collector insurance.
- **DoctorShield** — medical professional indemnity for specialist surgeons, clinics, and physicians.
- **Jaguar Transit** — high-value transit insurance, diamond logistics, and secured high-risk cargo protection.

### Challenges
1. **Strict Southeast Asian regulatory scrutiny** — MAS, BNM, and OIC impose real penalties for misleading claims, unverified guarantees, or missing statutory disclaimers.
2. **Multi-brand voice fragmentation** — three distinct tonal guidelines across five languages and multiple platforms.
3. **The "stateless AI" gap** — off-the-shelf LLMs repeat the same compliance and stylistic errors because human corrections vanish after review instead of updating prompt memory.
4. **Production bottlenecks** — turning a content idea into an actually-published, actually-compliant, actually-approved video or post normally takes a real production team days.
5. **Lead conversion latency** — finding, qualifying, and reaching out to real prospects manually bottlenecks the sales pipeline.

---

## 💡 2. What This System Actually Does

End to end, this is one connected pipeline, not a set of disconnected demo screens:

```
Research / Competitor Intel  →  Content Generation  →  Repurposing + Localization
        →  Compliance Gate  →  Human Review  →  Approved Content
        →  (optional) Video Generation: AI visuals + voiceover + captions + FFmpeg assembly
        →  Video Compliance  →  Human Approval
        →  Real LinkedIn Publishing (OAuth, member posting)
        →  Lead Discovery (real businesses via Google Places, or Groq-assisted profiles)
        →  Personalized Outreach  →  Outreach Compliance  →  Human Approval
        →  Real SMTP Email Delivery
        →  Analytics (real engagement only, never fabricated)
        →  Feedback  →  Lessons Learned  →  Future Generation
```

Every arrow above is a real, working, tested code path — see [§9](#-9-real-vs-fallback--read-this-before-a-demo) for exactly which parts need an API key to go from "deterministic fallback" to "live."

---

## ✨ 3. Key Features

| Capability | Description |
|---|---|
| 🏢 **Multi-Brand Studio** | Native support for **Jade**, **DoctorShield**, and **Jaguar Transit**, each with a distinct brand voice, platform-specific copy, and A/B variation angles. |
| ⚡ **12-Rule Compliance Engine** | Deterministic regex/heuristic evaluation (prohibited superlatives, unverified guarantees, missing disclaimers, high-risk terms, and more) plus an optional LLM-assisted rewrite pass, producing an objective 0–100 score with reasons. |
| 🔄 **Closed-Loop Learning** | Editorial rejections and edits automatically synthesize structured, brand-scoped **Lessons Learned** that get retrieved and injected into future generation prompts — demonstrable as a real before/after. |
| 🌐 **Multilingual Localization** | English, Bahasa Melayu, Bahasa Indonesia, Thai, and Chinese — real LLM-driven adaptation when Groq is configured, brand-aware deterministic fallback otherwise. |
| 🎬 **Real Video Production** | Full pipeline: scene scripting → narration-duration budgeting → AI scene visuals → gTTS voiceover → burned-in captions → FFmpeg assembly into a real, playable, vertical (1080×1920) H.264/AAC MP4 — not a storyboard mockup. |
| 🖼️ **4-Tier Image Provider Cascade** | Gemini → Hugging Face → **local Stable Diffusion 1.5** (runs on your own GPU, no API key) → a clearly-labeled branded fallback card. Every scene reports exactly which tier produced it — a fallback scene is never labeled "AI-generated." |
| 📣 **Real LinkedIn Publishing** | In-app OAuth (member posting, `w_member_social`) or a manually pasted token. Real text/image/video posts, idempotent (no duplicate posts), retried on transient failures, every attempt recorded. A background worker can auto-publish approved content on an interval — off by default. |
| 📧 **Real Email Outreach** | SMTP (Gmail or any standard provider) or a safe no-op mock. Outreach is drafted, compliance-checked, and requires explicit human approval before a real send is ever attempted. |
| 🎯 **Lead Discovery, Real and Assisted** | Real business discovery via the **Google Places API** (genuine names, addresses, phone numbers, websites) with real contact-email enrichment via **Hunter.io** or an SSRF-safe direct-site scrape — falls back to Groq-assisted or demo-pool profiles when no API key is configured. A transparent 5-factor 0–100 fit score either way. |
| 📊 **Real Analytics** | LinkedIn engagement numbers are only ever populated from a genuine successful API response — an honest "unavailable" otherwise, never an invented number. |
| 🔍 **Competitor Intelligence** | Real SSRF-safe website scraping, snapshot history, and mechanical change-detection between two points in time — a real diff, not an LLM guess. |

---

## 🏛️ 4. System Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌───────────────────┐
│   Research   │────▶│  Content Engine   │────▶│  Compliance Gate   │
│ / Competitor │     │ (Groq LLM + brand │     │ (12 deterministic  │
│  Scraper     │     │  voice + lessons) │     │  rules + LLM       │
└─────────────┘     └──────────────────┘     │  rewrite)          │
                                               └─────────┬──────────┘
                                                          ▼
                                              ┌───────────────────────┐
                                              │   Human Review Queue    │
                                              │ approve / reject / edit │
                                              └───────────┬─────────────┘
                             ┌─────────────────────────────┼─────────────────────────────┐
                             ▼                              ▼                              ▼
                  ┌───────────────────┐          ┌───────────────────┐          ┌───────────────────┐
                  │  Video Generation   │          │  Real Publishing    │          │  Feedback / Lessons │
                  │  scenes → 4-tier    │          │  (LinkedIn OAuth,   │          │  synthesized from    │
                  │  image cascade →    │          │  idempotent, retried,│          │  every reject/edit,  │
                  │  gTTS → captions →  │          │  worker optional)   │          │  re-injected into    │
                  │  FFmpeg MP4         │          │                     │          │  future generation   │
                  └───────────────────┘          └───────────────────┘          └───────────────────┘

┌────────────────────┐     ┌──────────────────────┐     ┌───────────────────┐     ┌──────────────┐
│  Lead Discovery      │────▶│  5-Factor Scoring     │────▶│  Governed Outreach  │────▶│  Real SMTP    │
│  Google Places +     │     │  (transparent,        │     │  (compliance + HITL │     │  Send (or     │
│  Hunter.io, or Groq   │     │  persisted breakdown) │     │  gate before send)  │     │  safe mock)   │
└────────────────────┘     └──────────────────────┘     └───────────────────┘     └──────────────┘
```

**Governance is not optional anywhere in this diagram.** No content reaches publishing without `status=='approved'` AND `compliance_status=='passed'`; no outreach email sends without its own separate approval; a background publishing worker exists but defaults to disabled and, even enabled, obeys the exact same gate.

See **[docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)** for the full technical breakdown (database schema, service-by-service responsibilities, state machines).

---

## 💻 5. Technology Stack

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.12+)
- **Data validation**: [Pydantic v2](https://docs.pydantic.dev/latest/)
- **ORM & database**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/) — SQLite for local dev/tests, PostgreSQL/Supabase-ready for production
- **LLM**: [Groq](https://groq.com/) (`groq/compound`), structured JSON mode, deterministic offline fallback when unconfigured
- **AI images**: Google Gemini, Hugging Face Inference Providers, local Stable Diffusion 1.5 (`diffusers`/`torch`, CUDA-accelerated)
- **Voice**: gTTS (free, no API key)
- **Video assembly**: FFmpeg (subprocess, auto-discovered)
- **Publishing**: LinkedIn REST API v2 + OAuth 2.0 (raw `httpx`, no SDK)
- **Email**: stdlib `smtplib` (SMTP) or a safe mock
- **Lead data**: Google Places API (New), Hunter.io, SSRF-safe direct scraping
- **Testing**: Pytest + FastAPI `TestClient` — **324 tests**, all external APIs mocked

### Frontend
- **Framework**: [React 19](https://react.dev/) + [Vite 8](https://vitejs.dev/)
- **Language**: [TypeScript 6](https://www.typescriptlang.org/)
- **Styling**: [Tailwind CSS v4](https://tailwindcss.com/)
- **Icons**: [Lucide React](https://lucide.dev/)
- **Testing**: [Vitest](https://vitest.dev/) + [React Testing Library](https://testing-library.com/react) — **19 tests**, all API calls mocked

---

## 📂 6. Repository Structure

```
ja-assure-ai-marketing-agent/
├── backend/
│   ├── app/
│   │   ├── main.py                        # FastAPI app, lifespan startup, optional background worker
│   │   ├── config.py                      # All environment-driven settings (one place, see §8)
│   │   ├── database/                      # SQLAlchemy engine & session
│   │   ├── models/entities.py             # ORM models (content queue, leads, competitors, publishing, …)
│   │   ├── schemas/                       # Pydantic request/response DTOs & agent contracts
│   │   ├── services/
│   │   │   ├── content_service.py          # Generation + lesson injection
│   │   │   ├── compliance_service.py       # 12-rule engine + LLM rewrite
│   │   │   ├── hitl_service.py             # Single source of truth for approval state machine
│   │   │   ├── lessons_service.py          # Feedback → lesson synthesis
│   │   │   ├── research_service.py         # SSRF-safe competitor scraping + change detection
│   │   │   ├── lead_service.py             # 5-factor scoring, outreach drafting
│   │   │   ├── lead_discovery_providers.py # Real Google Places + Hunter.io/scrape enrichment
│   │   │   ├── url_safety.py               # SSRF-safe URL validation (self-contained)
│   │   │   ├── localization_service.py     # 5-language adaptation
│   │   │   ├── video_generation_service.py # Full video pipeline orchestration
│   │   │   ├── video_providers.py          # 4-tier image cascade (Gemini/HF/SD1.5/fallback)
│   │   │   ├── voice_service.py            # gTTS narration
│   │   │   ├── caption_service.py          # SRT caption generation
│   │   │   ├── linkedin_client.py          # Low-level LinkedIn REST calls
│   │   │   ├── linkedin_oauth.py           # OAuth 2.0 member-posting flow
│   │   │   ├── publishing_service.py       # Gated, idempotent, retried LinkedIn dispatch
│   │   │   ├── publishing_worker.py        # Optional background auto-publish loop
│   │   │   ├── email_provider.py           # SMTP / mock email abstraction
│   │   │   └── analytics_service.py        # Real engagement fetch, honest "unavailable"
│   │   ├── api/v1/                        # REST routers — see docs/TESTING_GUIDE.md for the full map
│   │   └── agents/                        # Thin adapters exposing services via a generic dispatcher
│   ├── tests/                              # 324 tests
│   ├── requirements.txt
│   └── .env.example                        # Every setting, documented, no real values
├── frontend/
│   ├── src/
│   │   ├── components/                     # Dashboard, Content Studio, Review Center, Competitor Intel,
│   │   │   │                                #   Leads, Publishing, Learning, Analytics
│   │   │   └── */*.test.tsx                 # Vitest component tests
│   │   ├── services/api.ts                 # Typed API client — one function per backend endpoint
│   │   ├── types/index.ts                  # Shared TypeScript domain models
│   │   └── App.tsx                         # Central state + data-fetching orchestrator
│   └── package.json
├── docs/
│   ├── architecture/ARCHITECTURE.md        # Full technical architecture
│   ├── USER_GUIDE.md                       # How to operate the product, screen by screen
│   ├── RUNBOOK.md                          # Exact install/run/troubleshoot commands
│   ├── TESTING_GUIDE.md                    # Every API endpoint with example requests
│   ├── INTEGRATION_STATUS.md               # Requirement-by-requirement real/partial/blocked status
│   └── FINAL_SYSTEM_AUDIT.md               # Live-tested evidence for every major claim
├── database/supabase_schema.sql            # Optional Postgres/Supabase DDL
└── .gitignore                              # .env, *.db, generated media all excluded
```

---

## 🚀 7. Quick Start

```powershell
# Backend
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Edit backend\.env: set DATABASE_URL=sqlite:///./dev.db for zero-setup local dev.
# Everything else can stay blank -- the system runs fully in offline/demo mode.
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

```powershell
# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

- Backend: `http://127.0.0.1:8000` — Swagger UI at `http://127.0.0.1:8000/docs`
- Frontend: `http://localhost:5173`

**For the complete install guide** (FFmpeg, local Stable Diffusion 1.5, LinkedIn OAuth setup, SMTP setup, troubleshooting) **see [docs/RUNBOOK.md](docs/RUNBOOK.md)** — it has the exact command for every step, not a paraphrase.

---

## 🔑 8. Environment Variables

Every variable lives in `backend/.env` (copy from `.env.example`, which documents every field inline). Nothing is required to run the system — every external integration is optional and degrades to an honest, clearly-labeled fallback when unconfigured:

| Category | Variables | Effect when unset |
|---|---|---|
| Database | `DATABASE_URL` | Defaults to a Postgres placeholder; set to `sqlite:///./dev.db` for zero-setup local dev |
| LLM | `GROQ_API_KEY`, `GROQ_MODEL` | Deterministic offline fallback everywhere (compliance/localization/content still work) |
| AI images | `IMAGE_PROVIDER`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `HF_TOKEN`, `SD15_*` | Cascades to the next tier; branded fallback always works with zero config |
| LinkedIn | `LINKEDIN_CLIENT_ID/SECRET/REDIRECT_URI`, `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_ORGANIZATION_ID` | Publish attempts fail honestly rather than faking success |
| Email | `EMAIL_PROVIDER`, `SMTP_*` | `mock` (default) never sends real email |
| Lead data | `GOOGLE_MAPS_API_KEY`, `HUNTER_API_KEY` | Lead discovery uses Groq-assisted/demo-pool profiles instead of real businesses |
| Worker | `PUBLISH_WORKER_ENABLED`, `PUBLISH_WORKER_INTERVAL_SECONDS` | Automatic background publishing stays off (safe default) |

**Full table with every field and its default → [docs/RUNBOOK.md §2](docs/RUNBOOK.md#2-environment-variables).**

---

## ⚖️ 9. Real vs. Fallback — Read This Before a Demo

This system is built so that **every screen tells you the truth about what actually happened.** Before demoing, know which tier you're on:

| Feature | Real requires | Without it |
|---|---|---|
| LLM-generated copy, localization, compliance rewrite | `GROQ_API_KEY` | Deterministic templates — still compliant, still usable, just not LLM-written |
| AI scene visuals | `GEMINI_API_KEY` / `HF_TOKEN` / a local GPU + `pip install diffusers torch` | A clearly-labeled branded fallback card — **never** shown as "AI-generated" |
| Real LinkedIn post | LinkedIn Developer app + OAuth (see RUNBOOK §7) | Publish attempt returns an honest error, no fake success |
| Real email delivery | `EMAIL_PROVIDER=smtp` + real SMTP credentials | `mock` logs what would have been sent, never touches a real inbox |
| Real business leads | `GOOGLE_MAPS_API_KEY` (+ optional `HUNTER_API_KEY`) | Groq-assisted invented profiles or a demo pool — clearly tagged `AI_GENERATED_PROSPECT` / `DEMO_DATA`, never `VERIFIED_SOURCE` |
| Real LinkedIn engagement numbers | A LinkedIn token with read scope | An honest `"source": "unavailable"` payload, never an invented number |

The frontend's badges (`source_type`, provider labels, send/publish status) are wired directly to these real/fallback distinctions — see [docs/USER_GUIDE.md](docs/USER_GUIDE.md) for what each badge means on screen.

---

## 🧪 10. Automated Tests

```powershell
# Backend — 324 tests, zero real network calls, zero real credentials required
cd backend
venv\Scripts\activate
$env:DATABASE_URL="sqlite:///./test.db"; $env:GROQ_API_KEY=""
python -m pytest -q

# Frontend — 19 tests + a production build check
cd frontend
npm test
npm run build
```

No automated test ever sends a real email, posts to real LinkedIn, or calls a real paid API — every external call is mocked at the HTTP-client level. See **[docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md)** for the full endpoint-by-endpoint reference and the exact governance failure-mode checklist (what must return 400/409 and why).

---

## 📚 11. Documentation Index

| Document | For |
|---|---|
| **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)** | Operating the product day to day — every screen, every button, in plain language |
| **[docs/RUNBOOK.md](docs/RUNBOOK.md)** | Installing, running, and troubleshooting — exact commands |
| **[docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md)** | Every API endpoint, example requests, and the governance test matrix |
| **[docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)** | Full technical architecture, database schema, service responsibilities |
| **[docs/INTEGRATION_STATUS.md](docs/INTEGRATION_STATUS.md)** | Requirement-by-requirement status: real / partial / blocked, with evidence |
| **[docs/FINAL_SYSTEM_AUDIT.md](docs/FINAL_SYSTEM_AUDIT.md)** | Live-tested proof for every major claim (real video output, real SD1.5 generation, real SMTP send, etc.) |

---

## 🛡️ 12. Governance Guardrails

These are architectural, not aspirational — verified by direct API attack attempts during development, not just assumed:

1. **Nothing publishes without human approval.** `status=='approved' AND compliance_status=='passed'` is enforced server-side by a single `hitl_service.is_publishable()` check used everywhere content can leave the system — confirmed to reject every invalid state (pending, rejected, compliance-failed, edited-but-not-reapproved) via direct API calls, not just through the UI.
2. **Nothing is ever labeled AI-generated unless it genuinely was.** Every image, video scene, and text draft carries real provider/source metadata; a branded fallback is always named as a fallback.
3. **No outreach email sends without its own separate approval**, and never to a fabricated address — `Lead.email` is `None` until a real one is discovered or entered.
4. **Duplicate publishing is structurally prevented** — a second publish attempt on already-published content returns `409 Conflict`, never a silent no-op or a duplicate post.
5. **The background publishing worker defaults to disabled** and, even when enabled, calls the exact same gated, idempotent publish path a manual trigger does — there is no separate, less-governed automatic code path.
6. **Analytics never fabricates numbers.** A failed or unavailable engagement fetch is reported as `"unavailable"`, never as zero or an invented figure.
7. **Secrets stay out of the repository.** `.env`, all `*.db` files, and all generated media are gitignored; `.env.example` is the only tracked env file and contains no real values.

---

## 🔗 13. Repository

- **Repository**: [https://github.com/saalini-t/JA_ASSURE_AGENT](https://github.com/saalini-t/JA_ASSURE_AGENT)
- **Branch**: `main`
