from typing import Dict, List, Optional
from .base import BrandDNA
from .jade import JADE_BRAND_DNA
from .doctorshield import DOCTORSHIELD_BRAND_DNA

JA_ASSURE_BRAND_DNA = BrandDNA(
    id="ja_assure",
    name="JA Assure",
    domain="InsurTech & Specialized Commercial Underwriting",
    target_audience="Brokers, corporate partners, luxury business owners, and tech-driven enterprises",
    personality=["Visionary", "Authoritative", "Tech-Forward", "Trustworthy", "Innovative"],
    communication_style=["Forward-looking", "Analytical", "Precise", "Collaborative"],
    should_sound_like="An innovative regional InsurTech leader modernizing specialty niche underwriting with technology and trust.",
    should_not_sound_like="A legacy bureaucratic institution or an ungrounded crypto-fintech startup.",
    avoid_rules=[
        "Hype without substance",
        "Vague tech promises without insurance grounding",
        "Disrespecting established broker channels"
    ],
    core_value_props=[
        "Ecosystem of specialized insurance products (Jade, DoctorShield, etc.)",
        "Proprietary tech-enabled policy lifecycle and real-time binding",
        "Deep domain expertise in underserved specialty niches"
    ]
)

BRANDS: Dict[str, BrandDNA] = {
    "jade": JADE_BRAND_DNA,
    "doctorshield": DOCTORSHIELD_BRAND_DNA,
    "ja_assure": JA_ASSURE_BRAND_DNA
}

def get_brand(brand_id: str) -> BrandDNA:
    brand = BRANDS.get(brand_id.lower())
    if not brand:
        # Fallback to jade
        return JADE_BRAND_DNA
    return brand

def list_brands() -> List[Dict[str, str]]:
    return [
        {"id": b.id, "name": b.name, "domain": b.domain, "target_audience": b.target_audience}
        for b in BRANDS.values()
    ]
