# JA Assure AI Marketing Agent — Testing Guide

## 1. Running the automated test suites

### Backend (pytest)
```powershell
cd backend
venv\Scripts\activate
$env:DATABASE_URL="sqlite:///./test.db"
$env:GROQ_API_KEY=""
python -m pytest -q
```
- A fresh SQLite file avoids stale-schema issues after a model change (SQLite
  doesn't auto-migrate columns).
- `GROQ_API_KEY=""` is the standing convention for this suite — it forces the
  deterministic offline fallback path everywhere, so tests never depend on a
  live Groq quota.
- **No automated test ever sends a real email or makes a real LinkedIn/Gemini/
  Hugging Face API call.** External calls are either monkeypatched at the
  `httpx.AsyncClient` method level (LinkedIn, LinkedIn OAuth) or gated behind
  an explicit `EMAIL_PROVIDER=mock` monkeypatch (email) regardless of what
  your real `.env` has configured.

### Frontend (Vitest + build)
```powershell
cd frontend
npm test          # vitest run — component/unit tests, all API calls mocked
npm run build     # tsc -b && vite build — production build must compile clean
```

---

## 2. Complete API endpoint reference

Every route currently registered under `/api/v1`, taken directly from the
router source files (not paraphrased). Base URL: `http://127.0.0.1:8000/api/v1`.

### Health
| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | DB connectivity, LLM provider/mode, supported brands |

### Research & Competitor Intelligence
| Method | Path | Purpose |
|---|---|---|
| POST | `/research/run` | Full research pipeline (LLM analysis + demo fallback + optional URL scrape) |
| POST | `/research/scrape` | Scrape a single URL only, no persistence |
| POST | `/research/analyze` | Scrape + analyze + upsert a `Competitor` row |
| GET | `/competitors` | List competitors (`category` filter, `limit`) |
| GET | `/competitors/digest` | Change-detection digest for every competitor |
| GET | `/competitors/{comp_id}` | Single competitor |
| GET | `/competitors/{comp_id}/snapshots` | Full snapshot history (append-only) |
| GET | `/competitors/{comp_id}/digest` | Digest for one competitor |
| POST | `/competitors/analyze-url` | Scrape + analyze + upsert (same underlying call as `/research/analyze`) |
| POST | `/competitors` | Raw create, no scraping |

**Example**: register + digest
```
POST /research/run  {"brand":"jade","topic":"jewellery insurance","competitor_url":"https://example.com"}
GET  /competitors/digest
→ first call: has_change=false, note="baseline snapshot"
→ run again with a changed page: has_change=true, changed_fields=[...]
```

### Content Generation & Localization
| Method | Path | Purpose |
|---|---|---|
| POST | `/content/generate` | A/B copy variations for one brief |
| POST | `/content/campaign` | **One sequential call**: content generation → (optionally) real image/video generation → compliance → `ContentQueue`, replacing separate `/content/generate` + `/content/video` + `/content/video/enqueue` calls. Still lands in `human_review` — never auto-approved. |
| POST | `/content/suite` | Full multi-platform/language run → creates `ContentQueue` rows in `human_review` |
| POST | `/content/video` | Generate a video storyboard, optionally rendering a real MP4 |
| POST | `/content/video/enqueue` | Take a rendered `VideoScript` into the governed `ContentQueue` |
| POST | `/content/voice` | Standalone gTTS voiceover MP3 for a `VideoScript` |
| POST | `/agents/run/localization` | Localize arbitrary text into `ms`/`id`/`th`/`zh` (generic agent dispatcher) |

**Expected failure case**: `/content/suite` with an unsupported `platform` value → 422 validation error.

### Compliance
| Method | Path | Purpose |
|---|---|---|
| POST | `/compliance/check` | Run the compliance gate on arbitrary text |
| POST | `/compliance/rewrite` | Rewrite non-compliant text + re-check |
| GET | `/compliance/rules` | List all 12 registered compliance rules |

**Example**:
```
POST /compliance/check {"brand":"jade","content_text":"100% guaranteed coverage!"}
→ passed:false, violations:[{"rule_id":"RULE-01-GUARANTEED-OUTCOME","severity":"CRITICAL",...}]
```

### Human Review Queue (HITL)
| Method | Path | Purpose |
|---|---|---|
| GET | `/queue` | List (brand/platform/status/compliance_status filters) |
| GET | `/queue/pending` | Items in `human_review`/`pending` |
| GET | `/queue/approved` | Items in `approved`/`scheduled`/`published` |
| GET | `/queue/rejected` | Rejected items |
| GET | `/queue/{item_id}` | Single item |
| GET | `/queue/{item_id}/history` | Full decision audit trail |
| POST | `/queue/{item_id}/approve` | Approve (only legal from `human_review`) |
| POST | `/queue/{item_id}/reject` | Reject with `reason_tag`/`notes` — synthesizes feedback |
| POST | `/queue/{item_id}/edit` | Edit in place, re-runs compliance, returns to `human_review` |
| POST | `/queue/{item_id}/compliance` | Re-run compliance gate |
| POST | `/queue/{item_id}/regenerate` | Regenerate applying active lessons |
| POST | `/queue/{item_id}/rewrite` | Automated 1-click compliance rewrite |
| POST | `/queue` | Raw create (status clamped to `pending`) |
| PATCH | `/queue/{item_id}` | Partial update |
| DELETE | `/queue/{item_id}` | Delete |

**Governance test matrix** (every one of these must return 400/409, never succeed):
| Action | From status | Expected |
|---|---|---|
| approve | `pending` (compliance not yet checked) | rejected |
| approve | `rejected` | rejected |
| approve | already `approved` | rejected (no-op transition) |
| edit | `approved` | rejected — edits only legal pre-approval |
| publish (`/publishing/{id}` or `/publishing/{id}/linkedin`) | `human_review` | rejected |
| publish | `compliance_status != passed` | rejected, regardless of `status` |

### Feedback & Lessons (Learning Loop)
| Method | Path | Purpose |
|---|---|---|
| GET | `/feedback` | List (`reason_tag` filter) |
| POST | `/feedback` | Record feedback |
| GET | `/lessons` | List (`category` filter, `active_only`) |
| POST | `/lessons` | Create |
| PATCH | `/lessons/{lesson_id}/toggle` | Flip active flag |

**Learning demo** (before/after):
```
1. POST /content/suite {...}                    → note item id
2. POST /queue/{id}/reject {"reason_tag":"missing_disclaimer","notes":"..."}
3. GET  /lessons                                 → new lesson synthesized
4. POST /content/suite {... same brand/topic ...} → new draft's metadata/content
   reflects the lesson (compare against step 1's output)
```

### Leads
| Method | Path | Purpose |
|---|---|---|
| GET | `/leads` | List (industry/status filters) |
| POST | `/leads/discover` | LLM-invented or demo-pool prospect discovery + 5-factor scoring |
| GET | `/leads/outreach/{outreach_id}` | Fetch one outreach draft |
| POST | `/leads/outreach/{outreach_id}/approve` | Approve (HITL) |
| POST | `/leads/outreach/{outreach_id}/reject` | Reject |
| POST | `/leads/outreach/{outreach_id}/edit` | Edit, re-checks compliance, back to `human_review` |
| POST | `/leads/outreach/{outreach_id}/send` | Send email — **only if `status=='approved'` and the lead has a real email** |
| GET | `/leads/{lead_id}` | Single lead |
| POST | `/leads/{lead_id}/enrich` | Real URL scrape enrichment, or LLM/deterministic rationale |
| POST | `/leads/{lead_id}/outreach/generate` | Governed structured draft (HITL) — **use this one** |
| GET | `/leads/{lead_id}/outreach` | List all drafts for a lead |
| POST | `/leads/{lead_id}/outreach` | Legacy plain-string draft — **bypasses compliance, kept for backward compatibility only** |
| POST | `/leads` | Raw create |
| PATCH | `/leads/{lead_id}/status` | |

**Honest limitation**: `/leads/discover` never sources real public contact
data — it either asks the LLM to invent plausible-sounding prospect profiles
(explicitly instructed to leave email/phone blank) or draws from a 5-entry
hardcoded demo pool. `email` is `None` for every discovered lead, so
`/send` can only fire once a real email is added (e.g. via `PATCH`/manual
entry) and approved.

### Publishing
| Method | Path | Purpose |
|---|---|---|
| GET | `/publishing` | List all dispatch records (real + simulated) |
| GET | `/publishing/{record_id}` | Single record |
| POST | `/publishing` | Create a **simulated preview** dispatch (never calls LinkedIn) |
| POST | `/publishing/{content_id}/linkedin` | **Real** LinkedIn publish — gated, retried, idempotent |
| PATCH | `/publishing/{record_id}/cancel` | Cancel a simulated `scheduled` record |
| POST | `/publishing/{record_id}/analytics/refresh` | Real LinkedIn engagement fetch attempt (honest "unavailable" on failure) |
| POST | `/publishing/worker/run-once` | Manual one-shot worker pass |

**Idempotency test**:
```
POST /publishing/{id}/linkedin   → 200, external_post_id=urn:li:share:XXXX
POST /publishing/{id}/linkedin   → 409 Conflict, "already published"
```

### LinkedIn OAuth
| Method | Path | Purpose |
|---|---|---|
| GET | `/auth/linkedin/status` | `{oauth_configured, connected}` — never the token |
| GET | `/auth/linkedin/login` | Redirects to LinkedIn (or returns the URL as JSON with `?redirect=false`) |
| GET | `/auth/linkedin/callback` | OAuth redirect target — exchanges code for token |

### Analytics
| Method | Path | Purpose |
|---|---|---|
| GET | `/analytics/summary` | Dashboard KPIs |
| GET | `/analytics/engagement` | Real per-post engagement rows only (never fabricated) |

### Generic Agent Dispatcher
| Method | Path | Purpose |
|---|---|---|
| GET | `/agents/list` | Registered agent keys: `research, content, compliance, leads, feedback, localization, media, publishing` |
| POST | `/agents/run/{agent_name}` | Generic dispatch into any registered agent's `.run(payload)` |

---

## 3. Failure-mode checklist (run these explicitly, don't just assume)

| Scenario | Endpoint | Expected |
|---|---|---|
| Publish pending content | `POST /publishing/{id}/linkedin` | 400 |
| Publish compliance-failed content | same | 400, regardless of `status` |
| Publish rejected content | same | 400 |
| Publish already-published content | same | 409 |
| Send outreach before approval | `POST /leads/outreach/{id}/send` | 400 |
| Send outreach with no verified email | same | 400, "no verified email" |
| LinkedIn publish with no token configured | same | 400 or record `status=failed`, `error_info` set — never a fake success |
| SMTP send with bad credentials | same | `send_status=failed`, `send_error` populated — never marked `sent` |
| OAuth callback with tampered/reused `state` | `GET /auth/linkedin/callback` | 400 |
| Worker run with nothing eligible | `POST /publishing/worker/run-once` | `{"processed": 0, "results": []}` |
