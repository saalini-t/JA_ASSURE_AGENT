# 🛡️ JA Assure AI Marketing Agent

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-v4-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![Python](https://img.shields.io/badge/Python-3.13+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-F55036.svg?logo=groq&logoColor=white)](https://groq.com/)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E.svg?logo=supabase&logoColor=white)](https://supabase.com/)
[![Tests](https://img.shields.io/badge/Tests-19%20Passed-success.svg)](#-verification--automated-tests)

> **An autonomous, multi-brand agentic marketing, regulatory compliance, and lead intelligence platform for JA Assure across Southeast Asia.**

---

### 🌟 Core Differentiator

> **"Human feedback becomes persistent lessons that influence future AI generations."**
> 
> Unlike standard generative AI tools that repeat the same editorial or compliance mistakes, every human rejection or inline edit in JA Assure automatically synthesizes structured, persistent **Lessons Learned**. These lessons are dynamically queried and injected into future prompt contexts, creating a self-improving, brand-aligned marketing engine.

---

## 📑 Table of Contents
1. [Problem Statement](#-1-problem-statement)
2. [Proposed Solution](#-2-proposed-solution)
3. [Key Features](#-3-key-features)
4. [System Architecture & Agent Workflow](#-4-system-architecture--agent-workflow)
5. [Technology Stack](#-5-technology-stack)
6. [Repository Structure](#-6-repository-structure)
7. [Setup & Quick Start](#-7-setup--quick-start)
8. [Environment Variables](#-8-environment-variables)
   - 8b. [Stable Diffusion 1.5 (Local) Setup](#️-8b-stable-diffusion-15-local-setup--optional)
9. [Verification & Automated Tests](#-9-verification--automated-tests)
10. [End-to-End Demo Walkthrough](#-10-end-to-end-demo-walkthrough)
11. [Intentional Prototype Scope & Guardrails](#-11-intentional-prototype-scope--guardrails)
12. [GitHub Repository](#-12-github-repository)

---

## 🎯 1. Problem Statement

JA Assure manages specialized, high-value insurance portfolios across Singapore, Malaysia, Thailand, and Indonesia:
- **Jade**: High-net-worth bespoke luxury jewellery, watch, and private collector insurance.
- **DoctorShield**: Medical professional indemnity for specialist surgeons, clinics, and physicians.
- **Jaguar Transit**: High-value transit insurance, diamond logistics, and secured high-risk cargo protection.

### Challenges:
1. **Strict Southeast Asian Regulatory Scrutiny**: Authorities like the Monetary Authority of Singapore (MAS), Bank Negara Malaysia (BNM), and Office of Insurance Commission (OIC) impose severe penalties for misleading statements, unverified guarantee claims, or omission of statutory intermediary disclaimers.
2. **Multi-Brand Voice Fragmentation**: Marketing teams struggle to preserve distinct tonal guidelines across multiple languages (EN, MS, ID, TH, ZH) and platforms (LinkedIn, Instagram, TikTok, Video Storyboards).
3. **The "Stateless AI" Gap**: Off-the-shelf LLMs repeat the same compliance and stylistic errors because human editorial rejections are discarded after review instead of permanently updating prompt memory.
4. **Lead Conversion Latency**: Identifying high-value prospects, calculating underwriting qualification fit, and crafting personalized outreach manually bottlenecks sales pipelines.

---

## 💡 2. Proposed Solution

The **JA Assure AI Marketing Agent** deploys an integrated multi-agent system ("The Brain") built around a strict compliance safety net and closed-loop feedback memory:

- **Research Agent**: Collects competitor movements, insurance industry updates, and localized regulatory notices.
- **Content Agent**: Drafts campaign briefs into platform-optimized copy with A/B variation angles (ROI vs. Emotional Peace of Mind), pulling relevant lessons learned directly from Supabase PostgreSQL.
- **Compliance Gate (6-Rule Hybrid Engine)**: Evaluates content against statutory criteria, detects prohibited superlatives ("100% covered", "best in SG"), verifies mandatory disclaimers, and outputs an objective 0–100 compliance score.
- **Mandatory Human Review Center**: Prevents unauthorized automated publishing. Marketers can **Approve**, **Reject** with categorized reasons, **Edit** inline, or trigger a **1-Click AI Compliance Rewrite**.
- **Closed-Loop Feedback Agent**: Converts human rejection reasons and diff edits into generalized, brand-scoped persistent rules stored in Supabase PostgreSQL, feeding back into future prompt generations.
- **Lead Intelligence Agent**: Evaluates B2B prospects across 5 transparent criteria (0–100 Fit Score) and crafts personalized outreach sequences referencing prospect pain points.

---

## ✨ 3. Key Features

| Capability | Description |
|---|---|
| 🏢 **Multi-Brand Studio** | Native support for **Jade**, **DoctorShield**, and **Jaguar Transit**, tailored to their distinct brand voices and risk domains. |
| ⚡ **6-Rule Compliance Engine** | Deterministic regex + heuristic evaluation detecting prohibited superlatives, unverified savings, missing disclaimers, and high-risk terms. |
| 🔄 **Closed-Loop Learning** | Editorial rejections automatically extract actionable rules (e.g., *"Always clarify worldwide coverage limits"*), incrementing frequency counters and influencing future drafts. |
| 🛡️ **1-Click Compliance Rewrite** | Automatically rewrites non-compliant copy by stripping prohibited superlatives and appending mandatory statutory disclaimers while preserving marketing hook. |
| 🌐 **Multilingual Localization** | Generates natively in **English (EN)**, **Bahasa Melayu (MS)**, **Bahasa Indonesia (ID)**, **Thai (TH)**, and **Chinese (ZH)**. |
| 🎬 **Video / Reels Storyboarder** | Generates 30–60 second multi-scene video scripts complete with visual cues, voiceover scripts, on-screen text overlays, and audio direction. |
| 🎯 **Lead Intelligence & Scoring** | 5-factor scoring algorithm (0–100) evaluating Industry Fit, Risk Exposure, Premium Capacity, Geographic Fit, and Digital Footprint. |
| 📊 **Real-Time Analytics** | Complete executive dashboard tracking content lifecycle metrics, compliance distribution, rejection causes, and learning metrics. |
| 📅 **Simulated Publishing Dispatch Preview** | Human-controlled scheduling workflow storing records in Supabase PostgreSQL with strict human approval gates. Explicitly simulated with zero external social API claims. |
| 📴 **Offline Deterministic Fallback** | Seamlessly operates in full interactive demo mode when Groq API keys are absent or network is restricted. |

---

## 🏛️ 4. System Architecture & Agent Workflow

```mermaid
flowchart TD
    subgraph Research & Memory
        R[Research Agent] -->|Competitor & Market Context| CS[Content Service]
        LL[(Supabase PostgreSQL)] -->|Historical Rejection Rules| CS
    end

    subgraph Content Studio
        Brief[User Campaign Brief] --> CS
        CS -->|Prompt Assembly + Groq LLaMA 3.3| Gen[Generated Variations A/B]
        Gen --> CG[Compliance Gate Evaluator]
    end

    subgraph Compliance & Human Review
        CG -->|Score 0-100 + Violations| RC[Review Center: Pending Queue]
        RC -->|Action: 1-Click Rewrite| CR[Compliance Rewrite Service]
        CR --> CG
        RC -->|Action: Approve| AQ[Approved Queue / Publishing Ready]
        RC -->|Action: Reject / Edit| FB[Feedback Agent]
    end

    subgraph Closed-Loop Learning
        FB -->|Synthesize Structured Lesson| LL
    end

    subgraph Parallel Lead Intelligence
        LeadData[Raw Prospect Ingestion] --> LA[Lead Scoring Agent]
        LA -->|5-Factor 0-100 Score| LD[Leads Dashboard]
        LD -->|1-Click Generate| PO[Personalized Outreach Draft]
    end
```

### Agent State Machine & Compliance Gate
1. **DRAFTING**: Content created by Content Agent incorporating DB lessons.
2. **EVALUATION**: Compliance Gate scans for 6 key rules:
   - `RULE-01-PROHIBITED-CLAIM`: Absolute guarantees ("100% covered", "guaranteed payout").
   - `RULE-02-UNVERIFIED-SAVINGS`: Unsubstantiated discounts ("cheapest in Singapore").
   - `RULE-03-MISSING-DISCLAIMER`: Mandatory intermediary advisory notice.
   - `RULE-04-SUPERLATIVE`: Excessive claims ("best insurer", "number one").
   - `RULE-05-PREMIUM-FINANCING`: High-risk financial advisories.
   - `RULE-06-UNAUTHORIZED-ADVICE`: Direct medical or legal recommendations.
3. **PENDING HUMAN REVIEW**: Stored in Supabase queue. **Never auto-approved**.
4. **HUMAN DECISION**:
   - **Approve**: Marked `approved`, timestamped, queued for publishing.
   - **Reject**: Captures reviewer note, extracts category, updates `lessons_learned`.
   - **Edit**: Saves updated text, diff analyzed, records refinement lesson.
   - **Rewrite**: Auto-sanitizes violations, recalculates compliance score.

---

## 💻 5. Technology Stack

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.13)
- **Data Validation & Schemas**: [Pydantic v2](https://docs.pydantic.dev/latest/)
- **ORM & Database**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/) with [Supabase](https://supabase.com/) PostgreSQL (`psycopg` psycopg3 binary driver)
- **LLM Orchestration**: [Groq](https://groq.com/) API (`llama-3.3-70b-versatile`) with structured JSON mode and resilient offline fallback
- **Testing**: Pytest with `fastapi.testclient` (19 automated tests)

### Frontend
- **Framework**: [React 19](https://react.dev/) + [Vite](https://vitejs.dev/)
- **Language**: [TypeScript 5.9](https://www.typescriptlang.org/)
- **Styling**: [Tailwind CSS v4](https://tailwindcss.com/)
- **Icons**: [Lucide React](https://lucide.dev/)

---

## 📂 6. Repository Structure

```
ja-assure-ai-marketing-agent/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI application & lifespan startup/seed
│   │   ├── config.py                   # Pydantic Settings & environment variables
│   │   ├── database/                   # SQLite engine & session management
│   │   ├── models/
│   │   │   └── entities.py             # 7 SQLAlchemy ORM models
│   │   ├── schemas/
│   │   │   ├── agent_contracts.py      # Strict agent interface contracts
│   │   │   └── dtos.py                 # REST API Request/Response DTOs
│   │   ├── services/
│   │   │   ├── pipeline_service.py     # "The Brain" Central Orchestrator
│   │   │   ├── content_service.py      # Smart generation with lesson injection
│   │   │   ├── compliance_service.py   # 6-rule hybrid compliance engine
│   │   │   ├── lessons_service.py      # Feedback synthesis & prompt injection
│   │   │   ├── research_service.py     # Market & competitor scraper
│   │   │   ├── lead_service.py         # 5-factor lead scoring & outreach
│   │   │   ├── localization_service.py # 5 Southeast Asian language handler
│   │   │   ├── media_service.py        # Video/Reels storyboard pipeline
│   │   │   └── analytics_service.py    # Metric aggregations & KPI calculation
│   │   ├── api/v1/                     # 11 REST API routers
│   │   └── agents/                     # Specialized agent adapters
├── database/
│   └── supabase_schema.sql             # Complete Supabase PostgreSQL DDL
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI application & lifespan startup/seed
│   │   ├── config.py                   # Pydantic Settings & environment variables
│   │   ├── database/                   # Supabase PostgreSQL session & connection pool
│   │   ├── models/
│   │   │   └── entities.py             # 7 SQLAlchemy ORM models
│   │   ├── schemas/
│   │   │   ├── agent_contracts.py      # Strict agent interface contracts
│   │   │   └── dtos.py                 # REST API Request/Response DTOs
│   │   ├── services/
│   │   │   ├── pipeline_service.py     # "The Brain" Central Orchestrator
│   │   │   ├── content_service.py      # Smart generation with lesson injection
│   │   │   ├── compliance_service.py   # 6-rule hybrid compliance engine
│   │   │   ├── lessons_service.py      # Feedback synthesis & prompt injection
│   │   │   ├── research_service.py     # Market & competitor scraper
│   │   │   ├── lead_service.py         # 5-factor lead scoring & outreach
│   │   │   ├── localization_service.py # 5 Southeast Asian language handler
│   │   │   ├── media_service.py        # Video/Reels storyboard pipeline
│   │   │   └── analytics_service.py    # Metric aggregations & KPI calculation
│   │   ├── api/v1/                     # 11 REST API routers
│   │   └── agents/                     # Specialized agent adapters
│   ├── tests/                          # 19 unit & integration tests
│   ├── requirements.txt
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── components/                 # Modular InsurTech Command Center components
│   │   │   ├── layout/                 # Sidebar & Header navigation
│   │   │   ├── dashboard/              # Executive command center & workflow visualizer
│   │   │   ├── content/                # 3-column AI Content Studio
│   │   │   ├── review/                 # Compliance Review Center & control gates
│   │   │   ├── competitors/            # Intelligence radar & market whitespace
│   │   │   ├── leads/                  # 5-factor scoring & B2B prospect discovery
│   │   │   ├── learning/               # Closed-loop AI memory & prompt injection
│   │   │   ├── analytics/              # Live Supabase metrics & SVG charts
│   │   │   └── common/                 # Modals (Publishing, Rejection, Edit, Lead)
│   │   ├── services/
│   │   │   └── api.ts                  # Axios/Fetch API client wrapper
│   │   ├── types/
│   │   │   └── index.ts                # TypeScript domain models
│   │   ├── App.tsx                     # Main AI SaaS Orchestrator (7 Views)
│   │   ├── main.tsx                    # React DOM root
│   │   └── index.css                   # Tailwind v4 directives & gold design system
│   ├── package.json
│   └── vite.config.ts
├── data/
│   └── seed/
│       └── seed_data.json              # Realistic seed records for all brands
├── scripts/
│   ├── seed_db.py                      # Database reset & seeding utility
│   ├── start_backend.bat               # One-click backend launcher (Windows)
│   └── start_frontend.bat              # One-click frontend launcher (Windows)
├── docs/                               # Architectural diagrams & specifications
├── .gitignore                          # Zero secret leakage protection
└── README.md
```

---

## 🚀 7. Setup & Quick Start

### Prerequisites
- **Python**: 3.11 or higher
- **Node.js**: v20.19+ or v22.12+ (required by the Vite 8 / Rolldown toolchain)
- **Supabase Account**: [https://supabase.com](https://supabase.com) (free cloud PostgreSQL)
- **FFmpeg**: required for AI video/Reels generation (Content Studio's video mode). Install via `winget install Gyan.FFmpeg` (Windows), `brew install ffmpeg` (macOS), or `apt install ffmpeg` (Linux). Everything else works without it; only video rendering needs it. The backend auto-discovers `ffmpeg`/`ffprobe` from `PATH`, and on Windows also checks common install locations (e.g. the WinGet package store) as a fallback in case a still-running process's `PATH` predates the install — but a fresh terminal/IDE restart after installing is still the most reliable fix. If auto-discovery ever can't find them, set `FFMPEG_PATH`/`FFPROBE_PATH` in `backend/.env` to the exact executable paths.

### Quick Launch (3-Step)

#### Step 1: Initialize Supabase PostgreSQL Database
1. Create a new project in your [Supabase Dashboard](https://supabase.com/dashboard).
2. Go to the **SQL Editor** in the left sidebar.
3. Open and copy the entire contents of [`database/supabase_schema.sql`](database/supabase_schema.sql).
4. Paste and click **Run**. All 7 production tables, foreign keys, triggers, and indexes are created.
5. In Supabase **Project Settings → Database**, copy your connection string (URI format with password).

#### Step 2: Start Backend API Server
```powershell
# 1. Create and activate Python virtual environment
python -m venv backend\venv
backend\venv\Scripts\activate

# 2. Install backend dependencies (Groq, psycopg3, FastAPI, SQLAlchemy 2.0)
pip install -r backend\requirements.txt

# 3. Configure backend/.env
# Set DATABASE_URL and GROQ_API_KEY (optional: fallback active if empty)

# 4. Seed database with rich sample data (Jade, DoctorShield, Jaguar Transit)
python scripts\seed_db.py

# 5. Start FastAPI server (Runs on port 8000)
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```
*Backend is now live at:* **`http://127.0.0.1:8000`**  
*Interactive Swagger UI:* **`http://127.0.0.1:8000/docs`**

#### Step 3: Start Frontend Dashboard
Open a new terminal window:
```powershell
cd frontend
npm install
npm run dev
```
*Frontend is now live at:* **`http://localhost:5173`**

---

## 🔑 8. Environment Variables

Create `.env` in `backend/` (optional; system includes full offline demo mode if no API key is provided):

```env
# Supabase PostgreSQL Database Connection String
# Example: postgresql+psycopg://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
# Or Transaction Pooler: postgresql+psycopg://postgres.[YOUR-PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
DATABASE_URL=postgresql+psycopg://postgres:your_supabase_password_here@db.your_supabase_project_ref.supabase.co:5432/postgres

# Groq API Configuration (Leave empty to use built-in intelligent fallback provider)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# AI image providers for video scene visuals (Content Studio's video mode).
# IMAGE_PROVIDER="auto" (default) cascades through the configured providers in
# priority order, stopping at the first real success: Gemini -> Hugging Face ->
# Stable Diffusion 1.5 (local) -> branded fallback card. Any provider that's
# unconfigured or fails is skipped in favor of the next one -- set IMAGE_PROVIDER
# to one specific value ("gemini" | "openai" | "huggingface" | "stable_diffusion"
# | "branded_fallback") to force that single provider instead of cascading.
IMAGE_PROVIDER=auto

# Google Gemini Images -- primary cloud provider. Get a key at https://aistudio.google.com/apikey
GEMINI_API_KEY=
GEMINI_IMAGE_MODEL=models/gemini-2.5-flash-image

# OpenAI Images API (optional/legacy cloud provider, not part of the default
# cascade unless IMAGE_PROVIDER=openai). Get a key at https://platform.openai.com/api-keys
OPENAI_API_KEY=

# Hugging Face Inference Providers -- optional cloud provider, second in the cascade.
# Get a token at https://huggingface.co/settings/tokens
HF_TOKEN=
HF_IMAGE_MODEL=black-forest-labs/FLUX.1-dev

# Stable Diffusion 1.5 -- local provider, third in the cascade, no API key needed.
# Requires a one-time `pip install diffusers torch` -- see section 8b below.
SD15_MODEL_PATH=runwayml/stable-diffusion-v1-5
SD15_DEVICE=auto
SD15_LOW_VRAM=False
SD15_NUM_INFERENCE_STEPS=25
SD15_GUIDANCE_SCALE=7.5
SD15_WIDTH=512
SD15_HEIGHT=768
SD15_SEED=-1

# Server Configuration
ENVIRONMENT=development
PORT=8000
HOST=127.0.0.1
DEBUG=True
LOG_LEVEL=INFO
DEFAULT_BRANDS=jade,doctorshield,jaguartransit
```

---

## 🖼️ 8b. Stable Diffusion 1.5 (Local) Setup — Optional

Stable Diffusion 1.5 is the **local, offline** third-priority image provider (after Gemini and Hugging Face, before the deterministic branded fallback card). It needs no API key or internet access once its model weights are downloaded, so it keeps the video pipeline able to produce real AI images even with both cloud providers unavailable/out of quota.

**This is intentionally NOT installed or downloaded automatically** — `torch` and `diffusers` are large (multi-GB) packages, and the SD 1.5 model weights are themselves ~4GB. Neither is pulled in by `pip install -r requirements.txt`, and nothing in `app/main.py`'s startup ever imports or loads them. The model is only loaded lazily, in memory, the first time a real (non-mocked) generation actually happens.

**One-time setup**, only if you want this provider active:

```powershell
# 1. Install the two additional dependencies (pick ONE torch line for your machine):

# CPU only (works everywhere, slow — a single 512x768 image can take 1-2+ minutes):
backend\venv\Scripts\pip install diffusers torch --index-url https://download.pytorch.org/whl/cpu

# NVIDIA GPU with CUDA 12.1 (much faster — seconds per image):
backend\venv\Scripts\pip install diffusers torch --index-url https://download.pytorch.org/whl/cu121

# 2. (Optional) Pre-download the model weights ahead of time instead of on first
#    use, so the first real video generation isn't the one paying the download cost:
backend\venv\Scripts\python -c "from diffusers import StableDiffusionPipeline; StableDiffusionPipeline.from_pretrained('runwayml/stable-diffusion-v1-5')"
```

**Configuration** (`backend/.env`, see section 8 above): `SD15_MODEL_PATH` accepts either a Hugging Face model id (downloaded to the local HF cache on first use, as above) or an already-downloaded local directory path. `SD15_DEVICE=auto` picks CUDA when available and falls back to CPU otherwise; set `SD15_LOW_VRAM=True` on a memory-constrained GPU to enable attention slicing and sequential CPU offload (slower, but fits in less VRAM).

**If `diffusers`/`torch` aren't installed, or CUDA isn't available when `SD15_DEVICE=cuda` is explicitly set**, the provider fails with a clear, typed error and the normal cascade/fallback mechanism takes over (Hugging Face or the branded card) — it never blocks startup and never silently produces a fake image.

Automated tests never require any of this — they mock the provider's generation call directly and pass with no GPU, no model download, and `torch`/`diffusers` genuinely absent.

---

## 🧪 9. Verification & Automated Tests

### Run Backend Test Suite (19 Automated Tests)
```powershell
backend\venv\Scripts\pytest -c backend\pytest.ini backend\tests -v
```
**Test Coverage Includes:**
- System health checks & Groq provider validation
- Competitor intelligence scraping & relevance retrieval
- Smart content generation with persistent lesson injection & A/B variants
- Compliance violation detection & automated compliance rewrite
- Queue approval, rejection, and inline edit workflows
- Closed-loop feedback synthesis into active lessons
- Lead scoring & personalized outreach generation
- Analytics KPI aggregation & health distributions
- Strict publishing governance (blocks unapproved/non-compliant content)
- Simulated publishing dispatch lifecycle & cancellation

### Verify Frontend Production Build
```powershell
cd frontend
npm run build
```
*(Transpiles TypeScript and compiles asset bundle with 0 errors).*

---

## 🎬 10. End-to-End Demo Walkthrough

Follow this step-by-step sequence to demo the full platform to evaluators:

### Step A: Executive Dashboard (`/`)
1. View overall content counts: Pending Review, Approved, Rejected.
2. Observe the **System Compliance Score** and active **Learned Rules** dynamically queried from Supabase.
3. Review recent activity feeds and quick-action shortcuts.

### Step B: Content Studio (`Content Studio` tab)
1. **Brand Selection**: Select **Jade**, **DoctorShield**, or **Jaguar Transit**.
2. **Platform & Language**: Choose **LinkedIn**, **Instagram**, or **Video/Reels Storyboard** in English, Malay, or Chinese.
3. **Draft Campaign**: Enter a brief:
   > *"Announce tailored medical indemnity policy updates for aesthetic clinic surgeons in Singapore with 24/7 legal counsel."*
4. **Click "Generate with AI Agent"**:
   - System retrieves market context and active lessons from Supabase.
   - Generates structured copy via Groq LLaMA 3.3 with both **Angle A (Professional / ROI)** and **Angle B (Peace of Mind / Empathy)**.
   - Evaluates compliance in real time and automatically pushes to the **Review Center**.

### Step C: Review Center (`Review Center` tab)
1. Filter by **Pending Review**.
2. Observe item with compliance warnings (e.g. Missing MAS disclaimer or unvetted superlative).
3. **Option 1: 1-Click Compliance Rewrite**:
   - Click **"Auto Rewrite"** on the card.
   - Watch the agent strip prohibited superlatives, inject required disclaimers, and elevate the compliance score from 65 to 100.
4. **Option 2: Reject & Learn**:
   - Click **"Reject"** on any draft.
   - Enter reason: *"Do not claim 100% immediate payout without quoting standard claim investigation terms."*
   - Submit. The draft is marked `rejected`.

### Step D: Closed-Loop Learning (`Learning & Feedback` tab)
1. Immediately navigate to the **Learning & Feedback** tab.
2. Notice your rejection was converted into a structured **Lesson Learned**:
   - Categorized as `regulatory_compliance`.
   - Frequency count incremented.
   - Stored in Supabase and tagged to the specific brand.
3. Generate new content in the Content Studio: notice this new lesson is automatically injected into the Groq generation prompt to prevent recurrence!

### Step E: Lead Intelligence (`Leads` tab)
1. View B2B prospects scored 0–100 across 5 objective metrics.
2. Select high-fit lead (e.g., **Dr. Kenneth Tan — Mount Elizabeth Medical Centre**).
3. Click **"View Prospect"** or **"Generate Outreach"** to see a bespoke pitch drafted specifically addressing his practice risk profile.

### Step F: Competitors & Analytics (`Competitors` and `Analytics` tabs)
1. **Competitor Intelligence**: Review scraped competitor movements, pricing shifts, and recommended JA Assure counter-strategies.
2. **Analytics**: Inspect real-time compliance score distribution, rejection breakdown by reason, and continuous learning velocity from Supabase PostgreSQL.

### Step G: Human-Controlled Publishing Dispatch Preview (`Review Center` → Approved Tab)
1. In the **Review Center**, switch to the **Approved** filter.
2. Only human-approved drafts feature the **"Schedule Dispatch Preview"** action (pending and rejected content cannot be scheduled).
3. Click **"Schedule Dispatch Preview"** to inspect the simulated platform card, verify destination routing, select target date/time, and confirm.
4. The dispatch record is persisted in Supabase with status `scheduled`.
5. View scheduled dispatches and operational logs under the **Analytics** workspace, with full capability to cancel or reschedule. Notice the explicit governance disclaimer: *"SIMULATED DISPATCH — No external post has been published."*

---

## 🛡️ 11. Intentional Prototype Scope & Guardrails

To preserve enterprise trust and transparent evaluation during hackathon judging, the platform explicitly enforces the following architectural guardrails:

1. **AI Video / Reels Storyboards (No False MP4 Rendering Claims)**:
   - The media agent generates structured production cue sheets and scene-by-scene storyboards (0–6s hooks, visual descriptions, voiceover scripts, on-screen text overlays, and statutory disclaimers).
   - The platform deliberately does not claim client-side raw MP4 video rendering, positioning itself as the creative AI director and cue sheet generator for production teams.

2. **Simulated Publishing Dispatch (Strict Governance Gate)**:
   - The Publishing Preview operates as a human-controlled simulation environment. All scheduled dispatches are persisted in Supabase PostgreSQL with state transitions (`scheduled`, `cancelled`).
   - Third-party social media OAuth connections (e.g., live LinkedIn or Meta Graph APIs) are intentionally disabled to guarantee that no unvetted marketing copy is ever pushed to live public channels.

3. **Ethical B2B Lead Prospecting (No Fabricated Contact Info)**:
   - Discovered leads and enriched prospects are generated using business intelligence analysis and algorithmic 5-factor scoring (Industry Fit, Company Profile, Geographic Fit, Product Relevance, Insurance Need).
   - The platform explicitly marks prospects as `AI-GENERATED PROSPECT` and never fabricates private phone numbers or personal emails as verified third-party data.

4. **Resilient AI Failover (Dual-Mode Execution)**:
   - When configured with a valid `GROQ_API_KEY`, the agent calls live Groq LLaMA 3.3 models (`llama-3.3-70b-versatile`).
   - In environments without active credentials, the system automatically falls back to deterministic mock generators, clearly labeled as `Offline Demo Fallback` rather than masquerading as live AI.

---

## 🔗 12. GitHub Repository

- **Repository**: [https://github.com/abhirambuilds/ja-assure-ai-marketing-agent.git](https://github.com/abhirambuilds/ja-assure-ai-marketing-agent.git)
- **Branch**: `main`
- **License**: MIT
- **Author**: Abhi Ram Reddy (`abhirambuilds`)

