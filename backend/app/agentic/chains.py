import json
import logging
import re
from typing import Dict, Any, List
from google import genai
from google.genai import types
from ..config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger("agentic_chains")

def get_client() -> genai.Client:
    return genai.Client(api_key=GEMINI_API_KEY)

import time

def invoke_live_agent(prompt: str, system_instruction: str) -> Dict[str, Any]:
    """
    Invokes Gemini in real time across verified high-capacity flash endpoints
    with automated failover protection. Zero mock data.
    """
    client = get_client()
    candidate_models = [
        "gemini-flash-latest",
        "gemini-3.1-flash-lite",
        "gemini-3.8-flash",
        "gemini-3.6-flash"
    ]
    
    last_err = None
    for model_name in candidate_models:
        for attempt in range(2):
            try:
                config = types.GenerateContentConfig(
                    temperature=0.35,
                    top_p=0.95,
                    system_instruction=system_instruction,
                    response_mime_type="application/json"
                )

                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config
                )

                text = response.text.strip() if response and response.text else "{}"
                if text.startswith("```"):
                    text = re.sub(r"^```(?:json)?\n?", "", text, flags=re.IGNORECASE)
                    text = re.sub(r"\n?```$", "", text)
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    start = text.find("{")
                    end = text.rfind("}")
                    if start != -1 and end != -1:
                        return json.loads(text[start:end+1])
                    return json.loads(text)
            except Exception as e:
                logger.warning(f"Live model {model_name} attempt {attempt+1} encountered: {e}")
                last_err = e
                time.sleep(1.5 * (attempt + 1))

    raise last_err or RuntimeError("All live Gemini models failed.")

# 1. Strategy Agent
def run_strategy_agent(
    brand_dna_prompt: str,
    audience_context: str,
    objective_context: str,
    topic: str,
    lessons_prompt: str
) -> Dict[str, Any]:
    system_instruction = f"""
You are the Senior Communications Strategist for an InsurTech marketing system.
Enforce the following Brand DNA and constraints:
{brand_dna_prompt}

AUDIENCE CONTEXT:
{audience_context}

OBJECTIVE CONTEXT:
{objective_context}

CLOSED-LOOP LESSONS LEARNED (Mandatory Rules from Past Human Reviews):
{lessons_prompt}
""".strip()

    prompt = f"""
TOPIC: "{topic}"

Formulate the definitive MESSAGE STRATEGY for this campaign. Return a JSON object:
{{
  "core_problem": "The operational vulnerability or liability exposure the audience faces",
  "audience_insight": "What the audience misunderstands about generic coverage or industry risk",
  "core_message": "The central thesis of the campaign",
  "supporting_points": [
    "Pillar 1: practical factor",
    "Pillar 2: operational reality",
    "Pillar 3: risk consideration"
  ],
  "desired_emotion": "e.g. clarity, confidence, reassurance",
  "cta": "Non-pushy, educational action aligned with brand rules"
}}
"""
    return invoke_live_agent(prompt, system_instruction)

# 2. Master Content Agent
def run_master_content_agent(
    brand_dna_prompt: str,
    strategy: Dict[str, Any]
) -> Dict[str, Any]:
    system_instruction = f"""
You are the Master Narrative Architect. Build the single source of truth for all channels.
{brand_dna_prompt}

MESSAGE STRATEGY:
- Core Problem: {strategy.get('core_problem')}
- Audience Insight: {strategy.get('audience_insight')}
- Core Thesis: {strategy.get('core_message')}
- Supporting Points: {json.dumps(strategy.get('supporting_points', []))}
- CTA Directive: {strategy.get('cta')}
""".strip()

    prompt = """
Generate the CANONICAL MASTER CONTENT OBJECT. Return a JSON object:
{
  "title": "Insightful, authoritative headline",
  "executive_summary": "Comprehensive 3-4 sentence core thesis",
  "key_arguments": [
    "Argument 1 with industry specificity",
    "Argument 2 addressing operational reality",
    "Argument 3 addressing policy mechanics"
  ],
  "real_world_context": "Specific operational example (e.g. consignments, vault protocols, or clinic documentation)",
  "claims_guardrails": [
    "Do not promise 100% risk immunity or unconditional payout guarantees",
    "Avoid aggressive sales language"
  ],
  "approved_disclaimer": "This information is for educational purposes only and does not constitute formal underwriting advice. Terms, conditions, and exclusions apply."
}
"""
    return invoke_live_agent(prompt, system_instruction)

# 3. Multi-Platform Repurposer Agent
def run_repurposer_agent(
    brand_dna_prompt: str,
    master: Dict[str, Any],
    strategy: Dict[str, Any]
) -> Dict[str, Any]:
    system_instruction = f"""
You are the Multi-Platform Repurposing Agent. Adapt the canonical master idea natively across channels:
- LinkedIn = Professional education, thought leadership, clear spacing, non-pushy CTA.
- Instagram = Visual communication (6-slide carousel with visual direction prompts for designers + caption).
- X = Short, hook-first post (<280 chars) and 3-tweet analytical thread.

{brand_dna_prompt}

MASTER IDEA:
Title: {master.get('title')}
Summary: {master.get('executive_summary')}
Real-world scenario: {master.get('real_world_context')}
CTA: {strategy.get('cta')}
""".strip()

    prompt = """
Adapt into native formats. Return a JSON object:
{
  "linkedin": {
    "hook": "Strong professional hook",
    "body_text": "Full LinkedIn post with hook, context, problem, insight, practical takeaway, and educational CTA",
    "call_to_action": "Consultative closing thought",
    "hashtags": ["#Brand", "#RiskManagement", "#BusinessInsurance"],
    "estimated_reading_time_min": 1.5
  },
  "instagram": {
    "carousel_slides": [
      { "slide_number": 1, "headline": "Slide 1 Hook", "body": "...", "visual_direction": "Minimalist luxury aesthetic..." },
      { "slide_number": 2, "headline": "Slide 2 Problem", "body": "...", "visual_direction": "..." },
      { "slide_number": 3, "headline": "Slide 3 Insight", "body": "...", "visual_direction": "..." },
      { "slide_number": 4, "headline": "Slide 4 Supporting Pillar", "body": "...", "visual_direction": "..." },
      { "slide_number": 5, "headline": "Slide 5 Practical Takeaway", "body": "...", "visual_direction": "..." },
      { "slide_number": 6, "headline": "Slide 6 CTA / Conclusion", "body": "...", "visual_direction": "..." }
    ],
    "caption": "Full Instagram caption with spacing and CTA",
    "hashtags": ["#Brand", "#IndustryEducation", "#CommercialProtection"]
  },
  "x": {
    "single_post": "Concise tweet under 260 characters",
    "thread_posts": [
      "1/3: Hook and opening insight...",
      "2/3: The operational trap...",
      "3/3: Practical takeaway..."
    ],
    "character_counts": [180, 200, 190]
  }
}
"""
    return invoke_live_agent(prompt, system_instruction)

# 4. A/B Experimentation Agent
def run_ab_experiment_agent(
    brand_dna_prompt: str,
    base_text: str,
    strategy: Dict[str, Any]
) -> Dict[str, Any]:
    system_instruction = f"""
You are the Experimentation & Growth Agent. Generate A/B test variations with explicit hypotheses.
- Variant A: Educational / Operational Insight hook
- Variant B: Question / Cognitive Audit hook

{brand_dna_prompt}
""".strip()

    prompt = f"""
BASE CONTENT:
\"\"\"{base_text}\"\"\"

Formulate an A/B experiment testing two distinct psychological angles. Return a JSON object:
{{
  "experiment_goal": "Evaluate educational authority versus question-led curiosity",
  "variation_a": {{
    "variation_id": "A",
    "hook_type": "Educational / Operational Insight",
    "hypothesis": "Practical operational framing attracts practitioners actively reviewing risk.",
    "hook": "...",
    "adapted_body": "Full body text for Variant A...",
    "target_metric": "Qualified consultation requests / saves"
  }},
  "variation_b": {{
    "variation_id": "B",
    "hook_type": "Question / Assumption Audit",
    "hypothesis": "Direct question challenging standard policy assumptions triggers comment engagement.",
    "hook": "...",
    "adapted_body": "Full body text for Variant B...",
    "target_metric": "Discussion replies and shares"
  }}
}}
"""
    return invoke_live_agent(prompt, system_instruction)

# 5. First-Class Compliance Gate Agent (Feature 6 from Hackathon Brief)
def run_compliance_gate_agent(
    content_text: str,
    brand_name: str,
    domain: str
) -> Dict[str, Any]:
    system_instruction = f"""
You are the Senior Insurance Regulatory Compliance Officer for {brand_name} ({domain}).
InsurTech marketing is strictly regulated. Check against this compliance rubric:
1. Coverage Guarantees: Absolutely NO claims of '100% covered', 'zero liability', 'guaranteed payout', or 'foolproof protection'.
2. Alarmist Tactics: Absolutely NO sensationalized fear tactics or catastrophe-mongering.
3. Over-promising: Ensure all coverage is qualified as subject to policy terms, underwriting conditions, and exclusions.
4. Professional Demeanor: Must reflect consultative advisory tone.
""".strip()

    prompt = f"""
CONTENT TO AUDIT:
\"\"\"{content_text}\"\"\"

Audit this content and return a JSON object:
{{
  "overall_score": 95,
  "brand_alignment_passed": true,
  "compliance_passed": true,
  "platform_fit_passed": true,
  "flags": [
    {{
      "severity": "high",
      "category": "compliance",
      "issue": "name_of_issue",
      "message": "Specific explanation and remediation advice"
    }}
  ],
  "recommendation": "Summary evaluation for human editor",
  "requires_human_attention": false
}}
"""
    return invoke_live_agent(prompt, system_instruction)

# 6. Feedback Learning Agent (Feature 8 from Hackathon Brief)
def run_feedback_learner_agent(
    brand_name: str,
    platform: str,
    original_text: str,
    edited_text: str,
    reviewer_notes: str
) -> Dict[str, Any]:
    system_instruction = f"""
You are the Closed-Loop Continuous Improvement Agent for {brand_name}.
A human marketing lead just revised or rejected AI-generated content.
Derive the institutional lesson learned so the engine gets measurably better on future runs.
""".strip()

    prompt = f"""
ORIGINAL AI DRAFT:
\"\"\"{original_text}\"\"\"

HUMAN REVISED VERSION:
\"\"\"{edited_text}\"\"\"

REVIEWER NOTES / REJECTION REASON:
\"{reviewer_notes}\"

Analyze what changed and return a JSON object:
{{
  "issue": "too_salesy OR inaccurate_claim OR off_brand_tone OR wrong_cta OR alarmist_language",
  "human_feedback": "Concise summary of what the human editor objected to",
  "rule_directive": "Permanent imperative rule for future generations to avoid this error"
}}
"""
    return invoke_live_agent(prompt, system_instruction)
