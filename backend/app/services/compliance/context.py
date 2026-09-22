import re
from typing import Dict, Any, Optional
from pydantic import BaseModel

class ComplianceContext(BaseModel):
    brand: str = "jade"
    product: str = "Jewellers Block & Haute Horlogerie Insurance"
    jurisdiction: str = "Singapore"
    platform: str = "linkedin"
    language: str = "en"
    disclaimer: str = "*Terms, conditions, and underwriting limits apply. Jade is underwritten by licensed partner insurers.*"
    regulatory_framework: str = "MAS Guidelines on Standards of Conduct for Financial Advisers / Intermediary Disclosures"

    @property
    def authority(self) -> str:
        return self.regulatory_framework

    @property
    def default_disclaimer(self) -> str:
        return self.disclaimer

    @property
    def brand_display(self) -> str:
        return BRAND_METADATA.get(self.brand, {}).get("title", self.brand.capitalize())

BRAND_METADATA = {
    "jade": {
        "title": "Jade",
        "default_product": "Jewellers Block, High-Net-Worth Luxury Jewellery & Haute Horlogerie Insurance",
        "product_type": "jewellery_insurance",
        "primary_risks": ["Valuation depreciation", "Worldwide transit theft", "Uncapped agreed-value loss"],
        "default_disclaimer": "*Terms, conditions, and underwriting limits apply. Jade is underwritten by licensed partner insurers.*"
    },
    "doctorshield": {
        "title": "DoctorShield",
        "default_product": "Medical Professional Indemnity & Clinical Practice Malpractice Insurance",
        "product_type": "medical_indemnity",
        "primary_risks": ["SMC/Medical Council disciplinary inquiries", "Patient surgical malpractice claims", "Retroactive liability gaps"],
        "default_disclaimer": "*DoctorShield is a medical professional indemnity policy underwritten by licensed partner insurers. Terms, conditions, and exclusions apply.*"
    },
    "jaguartransit": {
        "title": "Jaguar Transit",
        "default_product": "High-Value Secured Cargo & Precious Freight Transit Insurance",
        "product_type": "cargo_transit",
        "primary_risks": ["Port delay / warehouse storage exclusions", "Air freight runway transit theft", "Bonded cross-border trucking casualty"],
        "default_disclaimer": "*Jaguar Transit cargo insurance is underwritten by licensed partner insurers. Terms and conditions apply.*"
    }
}

JURISDICTION_METADATA = {
    "singapore": {
        "name": "Singapore",
        "aliases": ["sg", "singapore", "lion city"],
        "authority": "Monetary Authority of Singapore (MAS) / General Insurance Association of Singapore (GIA)",
        "disclaimer_clause": "JA Assure is an exempt insurance broker / licensed corporate intermediary in Singapore. Terms & conditions apply.",
        "currency": "SGD"
    },
    "malaysia": {
        "name": "Malaysia",
        "aliases": ["my", "malaysia", "kuala lumpur", "kl", "johor"],
        "authority": "Bank Negara Malaysia (BNM) / Persatuan Insurans Am Malaysia (PIAM)",
        "disclaimer_clause": "Tertakluk kepada terma, syarat kelulusan penajajaminan, dan Akta Perkhidmatan Kewangan Bank Negara Malaysia.",
        "currency": "MYR"
    },
    "indonesia": {
        "name": "Indonesia",
        "aliases": ["id", "indonesia", "jakarta"],
        "authority": "Otoritas Jasa Keuangan (OJK)",
        "disclaimer_clause": "JA Assure beroperasi sesuai ketentuan regulasi Otoritas Jasa Keuangan (OJK). Syarat dan ketentuan polis berlaku.",
        "currency": "IDR"
    },
    "thailand": {
        "name": "Thailand",
        "aliases": ["th", "thailand", "bangkok"],
        "authority": "Office of Insurance Commission (OIC Thailand)",
        "disclaimer_clause": "ข้อกำหนดและเงื่อนไขเป็นไปตามที่กรมธรรม์กำหนด ภายใต้การกำกับดูแลของ คปภ. (OIC Thailand).",
        "currency": "THB"
    },
    "hong kong": {
        "name": "Hong Kong",
        "aliases": ["hk", "hong kong", "hongkong"],
        "authority": "Insurance Authority (IA Hong Kong) / Code of Conduct for Licensed Insurance Intermediaries",
        "disclaimer_clause": "Insurance services arranged in accordance with Hong Kong Insurance Authority intermediary standards. Policy terms apply.",
        "currency": "HKD"
    }
}

def resolve_context(
    brand: Optional[str] = None,
    product: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    country: Optional[str] = None,
    platform: Optional[str] = None,
    language: Optional[str] = None,
    content_text: str = ""
) -> ComplianceContext:
    """
    Extracts, normalizes, and resolves compliance context based on explicit inputs
    and heuristic content analysis.
    """
    # 1. Resolve Brand
    brand_clean = (brand or "jade").strip().lower()
    if brand_clean not in BRAND_METADATA:
        # Heuristic detection from text if brand not recognized
        text_lower = content_text.lower()
        if "doctorshield" in text_lower or "doctor" in text_lower or "medical" in text_lower or "surgeon" in text_lower:
            brand_clean = "doctorshield"
        elif "transit" in text_lower or "cargo" in text_lower or "freight" in text_lower or "jaguar" in text_lower:
            brand_clean = "jaguartransit"
        else:
            brand_clean = "jade"
    brand_meta = BRAND_METADATA[brand_clean]

    # 2. Resolve Product
    resolved_product = product or brand_meta["default_product"]

    # 3. Resolve Jurisdiction
    raw_loc = (jurisdiction or country or "").strip().lower()
    resolved_jurisdiction = "Singapore"
    jur_meta = JURISDICTION_METADATA["singapore"]

    if raw_loc:
        for k, v in JURISDICTION_METADATA.items():
            if raw_loc == k or any(alias in raw_loc for alias in v["aliases"]):
                resolved_jurisdiction = v["name"]
                jur_meta = v
                break
    else:
        # Check text heuristics
        text_lower = content_text.lower()
        for k, v in JURISDICTION_METADATA.items():
            if any(re.search(rf"\b{re.escape(alias)}\b", text_lower) for alias in v["aliases"]):
                resolved_jurisdiction = v["name"]
                jur_meta = v
                break

    # 4. Resolve Platform & Language
    resolved_platform = (platform or "linkedin").strip().lower()
    resolved_lang = (language or "en").strip().lower()

    # 5. Assemble Context-Specific Mandatory Disclaimer
    disclaimer = f"{brand_meta['default_disclaimer']} [{jur_meta['name']} Edition - Intermediary notice under {jur_meta['authority']} guidelines]"

    return ComplianceContext(
        brand=brand_clean,
        product=resolved_product,
        jurisdiction=resolved_jurisdiction,
        platform=resolved_platform,
        language=resolved_lang,
        disclaimer=disclaimer,
        regulatory_framework=jur_meta["authority"]
    )


class ComplianceContextResolver:
    """Class wrapper around resolve_context for object-oriented callers."""
    @staticmethod
    def resolve(
        brand: Optional[str] = None,
        product: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        country: Optional[str] = None,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        content_text: str = ""
    ) -> ComplianceContext:
        return resolve_context(
            brand=brand,
            product=product,
            jurisdiction=jurisdiction,
            country=country,
            platform=platform,
            language=language,
            content_text=content_text
        )

