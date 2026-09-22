from .base import BrandDNA

DOCTORSHIELD_BRAND_DNA = BrandDNA(
    id="doctorshield",
    name="DoctorShield",
    domain="Medical Indemnity & Malpractice Protection",
    target_audience="Doctors, surgeons, clinic owners, and registered medical practitioners",
    personality=[
        "Professional",
        "Reassuring",
        "Responsible",
        "Knowledgeable",
        "Trustworthy",
        "Discreet"
    ],
    communication_style=[
        "Clear",
        "Calm",
        "Educational",
        "Objective",
        "Empathetic to clinical stress"
    ],
    should_sound_like="A knowledgeable professional partner who understands the high-stakes clinical realities, regulatory scrutiny, and emotional weight of medical practice.",
    should_not_sound_like="Fear-based medical advertising, ambulance chasing, or an aggressive insurance salesperson.",
    avoid_rules=[
        "Fear tactics or alarmist claims regarding lawsuits/disciplinary proceedings",
        "Guarantees or promises of legal outcomes ('we guarantee zero liability')",
        "Overstated protection claims",
        "Unverified medical legal statements",
        "Flippant, casual, or meme-like tone in medical contexts",
        "Sensationalizing medical errors or patient disputes"
    ],
    core_value_props=[
        "Comprehensive medical defense and legal representation support",
        "Protection for inquiries before Medical Councils and regulatory bodies",
        "Peace of mind allowing doctors to focus on patient clinical outcomes"
    ]
)
