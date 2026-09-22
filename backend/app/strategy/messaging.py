import json
from pydantic import BaseModel
from typing import List, Dict, Any
from ..brand.base import BrandDNA
from ..strategy.audience import AudienceProfile
from ..strategy.objectives import ObjectiveStrategy
from ..feedback.lessons import Lesson
from ..generation.gemini_client import call_gemini, clean_json_response

class MessageStrategy(BaseModel):
    core_problem: str
    audience_insight: str
    core_message: str
    supporting_points: List[str]
    desired_emotion: str
    cta: str
    lessons_applied: List[str]

def formulate_message_strategy(
    brand: BrandDNA,
    audience: AudienceProfile,
    objective: ObjectiveStrategy,
    topic: str,
    lessons: List[Lesson]
) -> MessageStrategy:
    """
    Step 1 in the Pipeline: Synthesizes Brand DNA + Audience Reality + Objective + Lessons
    into an unambiguous communication strategy.
    """
    lessons_prompt = "\n".join([f"- [Lesson #{i+1}] Issue: {l.issue}. Directive: {l.rule_directive}" for i, l in enumerate(lessons)])
    if not lessons_prompt:
        lessons_prompt = "No prior team corrections recorded yet."

    system_instruction = f"""
{brand.to_system_prompt_snippet()}

AUDIENCE CONTEXT:
Target: {audience.name} ({audience.role_description})
Key Concerns: {', '.join(audience.key_concerns)}
Misconceptions: {', '.join(audience.current_misconceptions)}

OBJECTIVE CONTEXT:
Objective: {objective.name}
Marketing Goal: {objective.marketing_goal}
CTA Style: {objective.cta_guideline}

HISTORICAL LESSONS LEARNED (Enforce these rules):
{lessons_prompt}
"""

    prompt = f"""
You are the Lead Marketing Strategist for {brand.name}.
Topic: "{topic}"

Formulate the definitive MESSAGE STRATEGY. Return ONLY a JSON object with this exact structure:
{{
  "core_problem": "Precise articulation of the operational or liability exposure the audience faces",
  "audience_insight": "What the audience currently misunderstands or overlooks",
  "core_message": "The single thesis of this campaign",
  "supporting_points": [
    "Pillar 1: practical factor",
    "Pillar 2: operational reality",
    "Pillar 3: risk consideration"
  ],
  "desired_emotion": "e.g. clarity, confidence, reassurance",
  "cta": "Non-pushy, educational action aligned with brand rules"
}}
"""

    raw_response = call_gemini(prompt, system_instruction=system_instruction, json_mode=True)
    
    if raw_response:
        try:
            data = clean_json_response(raw_response)
            return MessageStrategy(
                core_problem=data.get("core_problem", f"Specialized exposure in {brand.domain}"),
                audience_insight=data.get("audience_insight", f"{audience.name} often rely on generic protections that leave critical gaps."),
                core_message=data.get("core_message", f"Insurance for {brand.target_audience} must reflect their specific operational realities."),
                supporting_points=data.get("supporting_points", [
                    "Tailored coverage addresses unique high-value risks",
                    "Generic policies frequently exclude core industry activities",
                    "Consultative risk assessment protects business longevity"
                ]),
                desired_emotion=data.get("desired_emotion", "Confidence and clarity"),
                cta=data.get("cta", "Reflect on whether your current insurance setup accounts for these specialized factors."),
                lessons_applied=[l.id for l in lessons]
            )
        except Exception:
            pass

    # Resilient fallback synthesis
    return MessageStrategy(
        core_problem=f"Operational vulnerabilities and policy exclusion risks specific to {brand.domain}",
        audience_insight=f"{audience.name} frequently assume standard policies cover specialized operations, only discovering exclusions after a loss event.",
        core_message=f"Appropriate protection in {brand.domain} requires policies built around the industry's real daily workflow, not generic commercial templates.",
        supporting_points=[
            "High-value transit, custody, and regulatory exposures require specific endorsements",
            "Generic commercial packages routinely contain restrictive warranties",
            "A proactive risk evaluation prevents underinsurance and unexpected claim denials"
        ],
        desired_emotion="Confident awareness",
        cta="Take a moment to review whether your existing coverage truly matches your daily operations.",
        lessons_applied=[l.id for l in lessons]
    )
