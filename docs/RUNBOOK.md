# JA Assure AI Marketing Agent — Runbook

Exact commands to install, configure, run, and exercise this system on Windows
(the reference dev machine: NVIDIA RTX 3050 6GB laptop GPU, 32GB RAM). Every
command below is copy-pasteable from the repo root unless a `cd` is shown.

No real credentials appear anywhere in this file — every example uses a
placeholder (`your_xxx_here`) or is explicitly marked "value withheld."

---

## 1. Requirements

| Requirement | Version used in this repo | Notes |
|---|---|---|
| Python | 3.12.4 (3.11+ works) | `python --version` |
| Node.js | v20.20.2 (v20.19+/v22.12+) | required by Vite 8 |
| npm | 10.9.0 | ships with Node |
| Database | SQLite (default for local dev/tests) or PostgreSQL (Supabase-compatible) | see §2 |
| FFmpeg + ffprobe | any recent build | required for video rendering only |
| GPU (optional) | NVIDIA RTX 3050 6GB confirmed working | only needed for the local Stable Diffusion 1.5 image provider |
| CUDA | 12.4 build of PyTorch used (`torch==2.6.0+cu124`) | driver reports CUDA 13.0, which is backward compatible with cu124 wheels |

There is **no Ollama dependency anywhere in this codebase** — the mega-prompt
template mentions it, but this project's LLM provider is **Groq** (cloud API,
`groq` Python SDK), not a local Ollama server. Do not install Ollama for this
project; it is not read by any file here.

---

## 2. Environment Variables

All variables live in `backend/.env` (copy from `backend/.env.example`, which
has every field below with a safe blank/default value and inline comments —
that file is the authoritative source; this table is a summary).

| Variable | Default | Purpose |
|---|---|---|
| `ENVIRONMENT` | `development` | |
| `DEBUG` | `True` | |
| `CORS_ORIGINS` | `http://localhost:5173,...` | must include your frontend's origin |
| `DATABASE_URL` | Postgres placeholder | set to `sqlite:///./dev.db` for zero-setup local dev (see §3) |
| `GROQ_API_KEY` | empty | the actual text-generation LLM. Blank = deterministic offline fallback mode everywhere (compliance/localization/content still work, just template-based) |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Must be a model your Groq account actually has access to — check with `client.models.list()` if you swap accounts/keys; an invalid name fails with a real `404` that silently falls back to mock content (see FINAL_SYSTEM_AUDIT.md) |
| `IMAGE_PROVIDER` | `auto` | `auto` cascades Gemini → Hugging Face → local Stable Diffusion 1.5 → branded fallback. Or force one: `gemini`\|`openai`\|`huggingface`\|`stable_diffusion`\|`branded_fallback` |
| `GEMINI_API_KEY` / `GEMINI_IMAGE_MODEL` | empty / `models/gemini-2.5-flash-image` | image generation only — unrelated credential from the text LLM |
| `OPENAI_API_KEY` | empty | optional image provider, not in the default `auto` cascade |
| `HF_TOKEN` / `HF_IMAGE_MODEL` | empty / `black-forest-labs/FLUX.1-dev` | Hugging Face image tier |
| `GOOGLE_MAPS_API_KEY` | empty | Real business discovery via Google Places API (New). Blank = lead discovery stays on the Groq-invented-profile/demo-pool path. Get one at the Google Cloud Console with "Places API (New)" enabled. |
| `HUNTER_API_KEY` | empty | Real contact-email lookup via Hunter.io, tried before an SSRF-safe direct-website-scrape fallback (which needs no key). Get one at hunter.io/api-keys. |
| `SD15_MODEL_PATH` | `runwayml/stable-diffusion-v1-5` | HF model id or local path |
| `SD15_DEVICE` | `auto` | `auto`\|`cuda`\|`cpu` |
| `SD15_LOW_VRAM` | `False` | set `True` on a 6GB card |
| `SD15_NUM_INFERENCE_STEPS` | `25` | |
| `SD15_GUIDANCE_SCALE` | `7.5` | |
| `SD15_WIDTH` / `SD15_HEIGHT` | `512` / `768` | |
| `SD15_SEED` | `-1` | `-1` = random |
| `LINKEDIN_ACCESS_TOKEN` | empty | used directly for posting; filled automatically by the OAuth flow below, or paste one in manually |
| `LINKEDIN_ORGANIZATION_ID` | empty | optional — only used as a fallback if member-URN resolution fails; **not needed for member posting** |
| `LINKEDIN_CLIENT_ID` / `LINKEDIN_CLIENT_SECRET` | empty | LinkedIn Developer app credentials, for the in-app OAuth flow |
| `LINKEDIN_REDIRECT_URI` | `http://localhost:8000/api/v1/auth/linkedin/callback` | must exactly match what's registered in the LinkedIn app |
| `PUBLISH_WORKER_ENABLED` | `False` | safe default — automatic background LinkedIn publishing is OFF unless explicitly set `True` |
| `PUBLISH_WORKER_INTERVAL_SECONDS` | `60` | |
| `EMAIL_PROVIDER` | `mock` | `mock` never sends real email (safe default, zero setup). `smtp` sends real email — see §8 |
| `EMAIL_FROM` / `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` | empty / empty / `587` / empty / empty | only read when `EMAIL_PROVIDER=smtp` |
| `NARRATION_WORDS_PER_MINUTE` | `150.0` | narration-duration budgeting for video scenes |
| `FFMPEG_PATH` / `FFPROBE_PATH` | empty | only needed if auto-discovery can't find the binaries |
| `LOG_LEVEL` | `INFO` | |
| `DEFAULT_BRANDS` | `jade,doctorshield,jaguartransit` | |

Frontend has one optional variable: `VITE_API_URL` (in `frontend/.env`, defaults
to `http://localhost:8000/api/v1` if unset).

---

## 3. Installation

```powershell
# --- Backend ---
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Minimal working .env for local dev (SQLite, no external API keys required):
copy .env.example .env
# then edit backend\.env and set:
#   DATABASE_URL=sqlite:///./dev.db
# everything else can stay blank -- the whole system runs in offline/demo mode.

# --- Frontend ---
cd ..\frontend
npm install
```

### 3b. FFmpeg (required for video generation only)
```powershell
winget install Gyan.FFmpeg
```
Restart your terminal after installing so `PATH` picks it up. The backend also
auto-discovers common WinGet install locations as a fallback.

### 3c. Stable Diffusion 1.5 (optional, local image provider — third cascade tier)
Not installed by `requirements.txt` on purpose (large, GPU-oriented, not needed
for the rest of the app or the test suite). To activate it:

```powershell
cd backend
venv\Scripts\activate

# CUDA build (matches this repo's tested RTX 3050 setup):
pip install torch --index-url https://download.pytorch.org/whl/cu124
pip install diffusers transformers accelerate

# CPU-only fallback (works anywhere, much slower):
# pip install torch --index-url https://download.pytorch.org/whl/cpu
# pip install diffusers transformers accelerate
```
The model weights (~4-5GB) download automatically from Hugging Face on first
use (lazy-loaded inside `LocalSD15ImageProvider`, never at backend startup) and
are cached under `~\.cache\huggingface`. Set `SD15_LOW_VRAM=True` in `.env` if
you have 8GB or less VRAM. No `HF_TOKEN` is required for this specific model.

---

## 4. Start Backend

```powershell
cd backend
venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API base: `http://127.0.0.1:8000/api/v1`
- Interactive Swagger UI: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/api/v1/health`

Tables are created automatically on first startup (`Base.metadata.create_all`)
against whatever `DATABASE_URL` points to — no separate migration step for
SQLite. If you change a model's columns after a database file already exists,
delete the `.db` file and restart (SQLite doesn't auto-migrate columns).

---

## 5. Start Frontend

```powershell
cd frontend
npm run dev
```
- App: `http://localhost:5173`
- Requires the backend running at the URL in `VITE_API_URL` (defaults to
  `http://localhost:8000/api/v1`).

Production build (used to verify the frontend actually compiles cleanly):
```powershell
cd frontend
npm run build
```

---

## 6. Start Required Services

- **Database**: none to start separately for local dev — SQLite is a plain
  file (`dev.db`), created on backend startup. Only needed if you point
  `DATABASE_URL` at a real Postgres/Supabase instance.
- **Ollama**: not used anywhere in this codebase — skip.
- **FFmpeg**: not a running service — it's invoked as a one-shot subprocess
  per video render; just needs to be installed and on `PATH` (§3b).
- **Background publishing worker**: not a separate process — it runs as an
  `asyncio` task inside the same backend process, only when
  `PUBLISH_WORKER_ENABLED=true` (see §9's troubleshooting and the testing
  guide for how to verify it's actually polling).

---

## 7. LinkedIn Setup (Member Posting)

1. Go to https://www.linkedin.com/developers/apps and create an app (or open
   an existing one).
2. Under **Products**, request both:
   - **"Sign In with LinkedIn using OpenID Connect"**
   - **"Share on LinkedIn"**

   These two products together grant exactly the scopes this app requests:
   `openid`, `profile`, `w_member_social`. No organization/company-page
   product is needed for member posting.
3. Under **Auth → OAuth 2.0 settings → Authorized redirect URLs for your app**,
   add exactly:
   ```
   http://localhost:8000/api/v1/auth/linkedin/callback
   ```
4. Copy the **Client ID** and **Client Secret** from the Auth tab into
   `backend/.env`:
   ```
   LINKEDIN_CLIENT_ID=<paste>
   LINKEDIN_CLIENT_SECRET=<paste>
   LINKEDIN_REDIRECT_URI=http://localhost:8000/api/v1/auth/linkedin/callback
   ```
5. Restart the backend so it picks up the new `.env` values.
6. **Authorize**: with the backend running, open this URL directly in your
   browser (not Swagger — it needs to be a real top-level navigation so
   LinkedIn's own login/consent page can load):
   ```
   http://localhost:8000/api/v1/auth/linkedin/login
   ```
   Log in, approve access, and you'll be redirected back to a page that says
   "LinkedIn connected." This fills `LINKEDIN_ACCESS_TOKEN` automatically (both
   in memory and written back into `backend/.env`).
7. **Check status** any time (never reveals the token itself):
   ```
   GET http://localhost:8000/api/v1/auth/linkedin/status
   → {"oauth_configured": true, "connected": true}
   ```
8. **Test a publish** — see §10's LinkedIn workflow below. Every publish still
   requires `status=='approved'` AND `compliance_status=='passed'` on the
   content item; the OAuth flow only produces a token, it never bypasses that
   gate.

If you'd rather skip the in-app OAuth flow entirely, you can instead obtain a
token any other way you like (e.g. LinkedIn's own token generator tools) and
paste it directly into `LINKEDIN_ACCESS_TOKEN` — the publishing code path is
identical either way.

---

## 8. SMTP Setup (Real Email Outreach)

1. In your Google Account → **Security → 2-Step Verification → App passwords**,
   generate an app password for "Mail." (Requires 2-Step Verification to be
   enabled on the account.)
2. Set in `backend/.env`:
   ```
   EMAIL_PROVIDER=smtp
   EMAIL_FROM=your_address@gmail.com
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your_address@gmail.com
   SMTP_PASSWORD=<the 16-character app password>
   ```
   (Never commit this file — `backend/.env` is gitignored. Never paste the
   actual app password into documentation, chat, or logs.)
3. Restart the backend.
4. Any other standard SMTP provider (SendGrid's SMTP relay, Resend's SMTP
   endpoint, a self-hosted relay, etc.) works the same way — just change
   `SMTP_HOST`/`SMTP_PORT`/credentials accordingly.
5. **Automated tests never use this** — every test that reaches the send
   endpoint explicitly forces `EMAIL_PROVIDER=mock` via `monkeypatch`,
   regardless of what your local `.env` has configured, so `pytest` never
   sends a real email even if SMTP is live in your environment.
6. To go back to safe mode at any time: set `EMAIL_PROVIDER=mock`.

---

## 9. Endpoint-by-Endpoint Reference

See **[TESTING_GUIDE.md](TESTING_GUIDE.md)** for the complete, exact endpoint
list (method + path + purpose, taken directly from the current router code)
along with example requests and expected responses for every service.

---

## 10. Full End-to-End Demo (Swagger, `http://127.0.0.1:8000/docs`)

### A. Content generation → approval
```
POST /content/suite
  {"brand":"jade","topic":"Sub-limit gaps for bespoke jewellery",
   "platforms":["linkedin"],"content_types":["post"],"languages":["en"]}
→ note the returned id

GET /queue/{id}                        → confirm compliance_status
POST /queue/{id}/approve               → status becomes "approved"
```

### B. LinkedIn text posting
```
GET  /auth/linkedin/status             → confirm {"connected": true}
POST /publishing/{id}/linkedin         → real post; response has external_post_id
GET  /publishing                       → find the PublishingRecord, status="published"
```

### C. Video generation → approval → publish
```
POST /content/video
  {"brand":"jade","topic":"Why sub-limits fail luxury collections",
   "platform":"reel","target_duration":45}
→ poll response fields: render_status, video_url, scenes_generated,
  ai_generated_scene_count, fallback_scene_count

POST /content/video/enqueue            (body: the full VideoScript object
                                         returned above) → creates a
                                         ContentQueue row, content_type="reel"
POST /queue/{new_id}/approve
POST /publishing/{new_id}/linkedin     → LinkedIn video upload path (detected
                                         automatically from metadata_json's
                                         video_path, not a text-only post)
```

### D. Lead generation → outreach → SMTP send
```
POST /leads/discover     {"brand":"jade","country":"Singapore"}
GET  /leads                            → note a lead id
POST /leads/{lead_id}/outreach/generate
POST /leads/outreach/{outreach_id}/send        → expect 400 (not approved yet)
POST /leads/outreach/{outreach_id}/approve
POST /leads/outreach/{outreach_id}/send        → real send if EMAIL_PROVIDER=smtp
                                                  and the lead has a real email
```

### E. Analytics & feedback
```
GET  /analytics/summary
GET  /analytics/engagement
POST /feedback     {"content_id":..., "reason_tag":"...", "notes":"...",
                     "original_content":"..."}
GET  /lessons
```

---

## 11. Troubleshooting

| Symptom | Cause | Diagnose | Fix |
|---|---|---|---|
| LinkedIn publish returns 400 "not configured" | No `LINKEDIN_ACCESS_TOKEN` | `GET /auth/linkedin/status` | Complete §7 |
| LinkedIn publish returns 401/403 | Token expired/revoked/insufficient scope | Check the error body's `error_info` field on the `PublishingRecord` | Re-run the OAuth flow (§7 step 6) to get a fresh token |
| LinkedIn upload posts text instead of video | `metadata_json` on the ContentQueue row has no `video_path`, or the file doesn't exist on disk | `GET /queue/{id}` and inspect `metadata_json` | Use `POST /content/video/enqueue` (not `/content/suite`) to create the queue row, so `video_path` is set |
| SMTP send fails with an auth error | Wrong app password, or 2FA not enabled on the Google account | Check `send_error` field on the `LeadOutreach` response | Regenerate the Gmail app password; confirm `SMTP_USERNAME` matches `EMAIL_FROM` |
| FFmpeg not found | Not installed, or installed after the terminal/IDE started | `where ffmpeg` in a **fresh** terminal | `winget install Gyan.FFmpeg`, then open a new terminal; or set `FFMPEG_PATH`/`FFPROBE_PATH` explicitly |
| CUDA unavailable for SD1.5 | No NVIDIA GPU, or the CPU-only torch wheel was installed by mistake | `python -c "import torch; print(torch.cuda.is_available())"` | Reinstall torch with the correct `--index-url` (§3c), or set `SD15_DEVICE=cpu` |
| SD1.5 CUDA out-of-memory | 6GB VRAM is tight for fp16 SD1.5 at default settings | Watch `nvidia-smi` during generation | Set `SD15_LOW_VRAM=True` (enables attention slicing + sequential CPU offload); lower `SD15_WIDTH`/`SD15_HEIGHT` |
| Gemini image provider always fails | Free-tier quota exhausted (`429 RESOURCE_EXHAUSTED`) or no key | Check the `provider_error` field on the video result's `scene_image_sources` | Cascade automatically falls through to the next tier — this is expected behavior, not a bug, unless you forced `IMAGE_PROVIDER=gemini` explicitly |
| Hugging Face image provider fails | `402 Payment Required` (free tier exhausted) or no `HF_TOKEN` | Same `provider_error` field | Same — cascade handles it automatically in `auto` mode |
| TTS/voiceover missing from video | gTTS network call failed (it needs outbound internet, no API key) | Check backend logs for the TTS error | Retry — gTTS has no quota, only needs connectivity; check firewall/proxy |
| Database "no such column" error | SQLite file predates a model change (SQLite doesn't auto-migrate) | Compare the model in `app/models/entities.py` against the actual `.db` schema | Delete the `.db` file and restart the backend (dev-only; you lose local data) |
| CORS error in browser console | Frontend origin not in `CORS_ORIGINS` | Check the browser's Network tab for the exact origin | Add it to `CORS_ORIGINS` in `backend/.env` (comma-separated) |
| Frontend shows "AI Marketing API Unavailable" | Backend not running, or wrong `VITE_API_URL` | Visit `http://127.0.0.1:8000/api/v1/health` directly | Start the backend; fix `frontend/.env`'s `VITE_API_URL` |
| `pytest` fails with `ModuleNotFoundError: mutagen` (or similar) | Virtual environment not activated | `where python` should point inside `backend\venv` | `venv\Scripts\activate` before running `pytest` |
