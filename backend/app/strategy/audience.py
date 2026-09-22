from pydantic import BaseModel
from typing import List, Dict

class AudienceProfile(BaseModel):
    id: str
    name: str
    role_description: str
    key_concerns: List[str]
    current_misconceptions: List[str]
    scroll_stopping_triggers: List[str]
    recommended_content_angle: str

AUDIENCE_PROFILES: Dict[str, AudienceProfile] = {
    "jeweller": AudienceProfile(
        id="jeweller",
        name="Jewellery Business Owner / Artisan",
        role_description="Operates high-value retail stores, workshop studios, or bespoke gemstone design houses.",
        key_concerns=[
            "High inventory concentration and valuation fluctuations",
            "Theft, burglary, and hold-up risks at retail locations",
            "Transit and exhibition vulnerability (trade shows, consignment)",
            "Business interruption from supply or security events",
            "Underinsurance due to standard commercial policy exclusions"
        ],
        current_misconceptions=[
            "Assuming standard commercial fire & theft property insurance covers fine gems",
            "Believing courier or postal carrier basic insurance covers loose diamonds in transit",
            "Assuming staff custody during off-site viewings is automatically indemnified"
        ],
        scroll_stopping_triggers=[
            "Specific jewellery trade scenarios (consignment notes, gem show transit, bespoke piece appraisals)",
            "Policy exclusion warnings hidden in standard SME packages",
            "Practical risk mitigation tips for high-security showcases"
        ],
        recommended_content_angle="Educational & Advisory: Focus on closing coverage gaps that standard policies leave open."
    ),
    "doctor": AudienceProfile(
        id="doctor",
        name="Medical Practitioner / Specialist / Clinic Director",
        role_description="Active physicians, surgeons, and clinic owners balancing clinical care with regulatory liability.",
        key_concerns=[
            "Medical malpractice allegations and civil suits",
            "Singapore Medical Council (SMC) or regional board inquiries and disciplinary hearings",
            "Reputational damage to hard-earned professional standing",
            "Escalating legal defense costs even for unmerited claims",
            "Clinic staff vicarious liability"
        ],
        current_misconceptions=[
            "Thinking institutional hospital coverage provides unconditional personal protection for private practice",
            "Believing medical defense organizations always guarantee legal fees without discretionary limits",
            "Underestimating the mental and time strain of a formal regulatory inquiry"
        ],
        scroll_stopping_triggers=[
            "Inquiry procedures and how early legal counsel affects outcomes",
            "Case study analysis on documentation and informed consent",
            "Clarity on claims-made vs occurrence indemnity policies"
        ],
        recommended_content_angle="Calm, Objective & Empathetic: Address clinical stress with reassuring procedural clarity."
    ),
    "corporate_broker": AudienceProfile(
        id="corporate_broker",
        name="Insurance Broker / Financial Advisor / Corporate Client",
        role_description="Advises corporate clients on niche commercial risks and specialized underwriting.",
        key_concerns=[
            "Client retention and providing bespoke tailored coverage",
            "Speed of underwriting turnaround and binding authority",
            "Transparency in claims settlement"
        ],
        current_misconceptions=[
            "Specialty niche insurance is too slow and manual to scale",
            "Brokers lose control when utilizing InsurTech platforms"
        ],
        scroll_stopping_triggers=[
            "Underwriting efficiency benchmarks",
            "Niche market growth and emerging commercial liabilities"
        ],
        recommended_content_angle="Authoritative & Tech-Forward: Focus on speed, precision, and ease of placement."
    )
}

def get_audience_profile(audience_key: str) -> AudienceProfile:
    # Match key by substring or default to jeweller
    key_lower = audience_key.lower()
    if "doc" in key_lower or "medic" in key_lower:
        return AUDIENCE_PROFILES["doctor"]
    elif "broker" in key_lower or "corp" in key_lower:
        return AUDIENCE_PROFILES["corporate_broker"]
    return AUDIENCE_PROFILES["jeweller"]
