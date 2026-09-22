from pydantic import BaseModel, Field
from typing import List

class BrandDNA(BaseModel):
    id: str
    name: str
    domain: str
    target_audience: str
    personality: List[str]
    communication_style: List[str]
    should_sound_like: str
    should_not_sound_like: str
    avoid_rules: List[str]
    core_value_props: List[str]
    default_market: str = "Singapore"
    primary_language: str = "English"

    def to_system_prompt_snippet(self) -> str:
        return f"""
BRAND DNA: {self.name}
Domain: {self.domain}
Target Audience: {self.target_audience}
Brand Personality: {', '.join(self.personality)}
Communication Style: {', '.join(self.communication_style)}

SHOULD SOUND LIKE:
{self.should_sound_like}

SHOULD NOT SOUND LIKE:
{self.should_not_sound_like}

STRICT GUARDRAILS (DO NOT VIOLATE):
- {chr(10).join('- ' + rule for rule in self.avoid_rules)}
""".strip()
