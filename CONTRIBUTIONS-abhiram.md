# Contributor: Abhi Ram

## Role
Voice Agent & Complaints Handling

## Tech Stack
`FastAPI` `Python` `gTTS` `SQLite` `REST API (v1)`

---

## 1. Voice Agent
- Worked alongside Shalini on the voice agent — the speech layer used to narrate generated video content (gTTS-based text-to-speech).
- Focused on the input/handling side: turning script text into a clean voice-ready format before it's passed to speech synthesis.

**How it works**:
Content Agent produces the script → Voice Agent prepares and formats it → gTTS generates the audio → audio is handed to the video assembly step.

### Key Implementation Details:
- **Script Sanitization & Normalization**: Strips stage directions (`[Visual: ...]`, `(voiceover:)`), markdown syntax, raw URLs, and unpronounceable characters.
- **Regional Acronym & Currency Normalization**: Formats regional regulatory terms (`MAS` → `M-A-S`, `PDPA` → `P-D-P-A`, `MOH` → `M-O-H`, `AI` → `A-I`, `B2B` → `B-to-B`) and currencies (`S$` → `Singapore dollars`, `RM` → `Ringgit`, `HK$` → `Hong Kong dollars`, `USD` → `U-S dollars`) for natural speech pacing.
- **Cadence & Punctuation**: Cleans pauses and sentence terminators for optimal gTTS speech delivery.

---

## 2. Complaints Handling Flow
- Built the complaints handling flow — capturing user/customer complaint input, storing it (SQLite), and routing it for review/response, separate from the marketing content pipeline.

**How it works**:
Complaint is submitted → stored as a record in SQLite database → flagged/routed so it can be reviewed and actioned, with a status field similar in spirit to the content queue's pending → approved pattern.

### Specific Complaints Schema & Fields:
- **Table**: `complaints` (Model: `Complaint` in `backend/app/models/entities.py`)
- **Key Fields**:
  - `id`: Integer primary key, autoincrement
  - `complaint_number`: Formatted unique tracking ID (e.g. `CMP-20260922-A1B2C3`)
  - `customer_name`: Name of complainant
  - `customer_email`: Customer email address
  - `customer_phone`: Customer contact number (optional)
  - `brand`: Multi-brand tenant (`jade`, `doctorshield`, `jaguartransit`)
  - `category`: Complaint classification (`policy_coverage`, `claims_denial`, `billing_dispute`, `customer_service`, `compliance_misleading`, `technical_issue`, `other`)
  - `priority`: Urgency level (`low`, `medium`, `high`, `urgent`)
  - `subject`: Complaint headline
  - `description`: Detailed issue description
  - `status`: Lifecycle state (`pending` → `under_review` → `routed` → `actioned` → `resolved` / `rejected`)
  - `routed_to`: Target resolution department (`claims_desk`, `underwriting_team`, `compliance_legal`, `billing_support`, `executive_escalations`, `customer_relations`)
  - `routing_reason`: Explanation of routing decision
  - `routed_at`: Timestamp when routed
  - `assigned_reviewer`: Designee responsible for reviewing complaint
  - `response_draft`: Draft customer response
  - `resolution_notes`: Detailed notes on remediation/action taken
  - `actioned_by`: Officer taking action
  - `actioned_at`: Action timestamp
  - `resolved_at`: Resolution timestamp
  - `created_at` / `updated_at`: Audit timestamps

### Exact Routing Logic:
- **Claims Denial / Payout Disputes**: Auto-routed to `claims_desk`
- **Regulatory / Compliance / Misleading Disclosures**: Auto-routed to `compliance_legal`
- **Policy Wording & Underwriting Queries**: Auto-routed to `underwriting_team`
- **Billing / Invoicing / Payment Discrepancies**: Auto-routed to `billing_support`
- **Urgent / Legal Risk Triggers** (words such as `lawsuit`, `regulator`, `MAS`, `police`, `court`): Auto-escalated to `executive_escalations` with priority `urgent`
- **General Inquiries**: Auto-routed to `customer_relations`

---

## File Paths
- **Voice Agent Service**: `backend/app/services/voice_agent.py`
- **Voice TTS Pipeline**: `backend/app/services/voice_service.py`
- **Voice Agent Tests**: `backend/tests/test_voice_agent_prep.py`
- **Complaints Model**: `backend/app/models/entities.py`
- **Complaints DTOs & Schemas**: `backend/app/schemas/dtos.py`
- **Complaints Service & Routing Logic**: `backend/app/services/complaints_service.py`
- **Complaints REST API Router (v1)**: `backend/app/api/v1/complaints.py`
- **API Router Registry**: `backend/app/api/v1/api.py`
- **Complaints Integration Tests**: `backend/tests/test_complaints_flow.py`
