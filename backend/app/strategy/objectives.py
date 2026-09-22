from pydantic import BaseModel
from typing import Dict

class ObjectiveStrategy(BaseModel):
    id: str
    name: str
    marketing_goal: str
    cta_guideline: str
    tone_accent: str

MARKETING_OBJECTIVES: Dict[str, ObjectiveStrategy] = {
    "educate": ObjectiveStrategy(
        id="educate",
        name="Educational / Thought Leadership",
        marketing_goal="Deconstruct complex niche risks and explain why standard coverage falls short.",
        cta_guideline="Invite reflection or invite reading a detailed resource / speaking to an expert advisor without pressure.",
        tone_accent="Insight-driven, analytical, and supportive"
    ),
    "awareness": ObjectiveStrategy(
        id="awareness",
        name="Brand Awareness / Problem Recognition",
        marketing_goal="Highlight blind spots in existing insurance setups and establish category leadership.",
        cta_guideline="Encourage dialogue, asking relevant questions about business operations or risk reviews.",
        tone_accent="Eye-opening, authoritative, and relevant"
    ),
    "consideration": ObjectiveStrategy(
        id="consideration",
        name="Evaluation / Consideration",
        marketing_goal="Demonstrate specialized capability and prompt the business owner to review their current policy terms.",
        cta_guideline="Provide a clear, low-friction pathway to request a policy review or consultation.",
        tone_accent="Practical, reassuring, and consultative"
    )
}

def get_objective(obj_id: str) -> ObjectiveStrategy:
    return MARKETING_OBJECTIVES.get(obj_id.lower(), MARKETING_OBJECTIVES["educate"])
