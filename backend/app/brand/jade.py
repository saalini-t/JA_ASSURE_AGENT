from .base import BrandDNA

JADE_BRAND_DNA = BrandDNA(
    id="jade",
    name="Jade",
    domain="Jewellers Block Insurance",
    target_audience="Jewellery businesses, boutique jewellers, gemstone dealers, and watchmakers",
    personality=[
        "Premium",
        "Confident",
        "Knowledgeable",
        "Trustworthy",
        "Business-oriented"
    ],
    communication_style=[
        "Clear",
        "Concise",
        "Industry-aware",
        "Educational",
        "Professional"
    ],
    should_sound_like="An experienced insurance partner who understands the high-value realities, operational risks, and craftsmanship of jewellery businesses.",
    should_not_sound_like="A generic insurance advertisement, aggressive salesperson, or alarmist promoter.",
    avoid_rules=[
        "Excessive hype or buzzwords",
        "Fear-based messaging or scare tactics",
        "Unverified promises or absolute guarantees (e.g., '100% covered against any risk')",
        "Overly generic financial jargon",
        "Direct aggressive sales pitches (lead with education first before any CTA)",
        "Trivializing specialized vault, transit, or exhibition vulnerabilities"
    ],
    core_value_props=[
        "Tailored coverage for high-value inventory and consignment goods",
        "Protection covering premises, vault, transit, and exhibition risks",
        "Deep understanding of luxury and bespoke retail operations"
    ]
)
