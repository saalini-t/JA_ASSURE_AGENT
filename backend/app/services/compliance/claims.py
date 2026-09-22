import re
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.schemas.agent_contracts import ClaimItem
from app.services.llm_provider import llm_provider

logger = logging.getLogger("ja_assure.compliance.claims")

RISK_CLAIM_PATTERNS = [
    (r"100%\s*(guaranteed|risk[\s-]free|protection|payout|covered)", "guaranteed_outcome", "critical", "Guaranteed insurance outcome or payout"),
    (r"guaranteed\s*(payout|claim|approval|replacement|recovery)", "guaranteed_outcome", "critical", "Guaranteed claims settlement claim"),
    (r"covers?\s*(everything|all\s*losses?|anything|every\s*situation)", "unsupported_coverage", "critical", "Universal / all-loss coverage claim"),
    (r"unlimited\s*(coverage|protection|liability)", "unsupported_coverage", "critical", "Unlimited coverage limit claim"),
    (r"complete\s*(immunity|protection)", "absolute_protection", "high", "Absolute protection from all loss"),
    (r"no\s*questions?\s*asked", "false_certainty", "high", "Claim implying absence of claims investigation"),
    (r"cheapest\s*(in\s*the\s*country|in\s*asia|rates?|premiums?)", "pricing_superlative", "medium", "Superlative lowest price claim"),
    (r"lowest\s*(rates?|premiums?|prices?)", "pricing_superlative", "medium", "Lowest premium guarantee claim"),
    (r"better\s*than\s*(competitor|singmed|briteprotect)", "comparative_claim", "high", "Comparative disparagement of competitors"),
    (r"diagnos(e|is|ing)|treat(ment)?\s*guidelines?|cure|prescribe", "medical_advice", "critical", "Clinical medical diagnosis or treatment claim"),
    (r"automatic(ally)?\s*(paid|approved|issued|settled)", "automatic_payout", "critical", "Automatic payout / approval promise"),
    (r"every\s*(doctor|surgeon|practitioner)\s*is\s*(automatically\s*)?covered", "product_mismatch", "high", "Universal practitioner coverage claim"),
    (r"(99(\.9)?%|98%|95%)\s*(of\s*claims?\s*paid|customer\s*satisfaction)", "unsupported_statistic", "medium", "Unsourced quantitative statistic")
]

class ClaimsExtractionResponse(BaseModel):
    claims: List[ClaimItem] = Field(default_factory=list)

class ClaimExtractor:
    """
    Extracts marketing claims, categorizing them by claim type and initial regulatory risk level.
    Uses Groq LLM semantic parsing when live, supplemented by deterministic heuristic extraction.
    """

    async def extract_claims(
        self,
        content_text: str,
        brand: str,
        product: str,
        jurisdiction: str,
        skip_llm: bool = False
    ) -> List[ClaimItem]:
        extracted_claims: List[ClaimItem] = []
        seen_texts = set()

        # 1. Deterministic Claim Extraction
        for pattern, claim_type, risk_level, desc in RISK_CLAIM_PATTERNS:
            for match in re.finditer(pattern, content_text, re.IGNORECASE):
                # Extract surrounding clause or sentence
                start = max(0, match.start() - 30)
                end = min(len(content_text), match.end() + 30)
                clause = content_text[start:end].strip()
                matched_phrase = match.group(0).strip()
                
                if matched_phrase.lower() not in seen_texts:
                    seen_texts.add(matched_phrase.lower())
                    extracted_claims.append(
                        ClaimItem(
                            claim_text=matched_phrase,
                            claim_type=claim_type,
                            risk_level=risk_level,
                            explanation=f"{desc} (Context: '...{clause}...')".strip()
                        )
                    )

        # 2. Semantic Claim Extraction via Groq when live
        if not skip_llm and llm_provider.is_live and len(content_text.strip()) > 20:
            try:
                prompt = (
                    f"You are a regulatory claim extraction engine for insurance marketing in {jurisdiction}.\n"
                    f"Brand: {brand.title()} | Product: {product}\n\n"
                    f"Analyze this marketing text and extract all specific claims made (e.g. coverage promises, speed, pricing, guarantees, comparisons, stats):\n"
                    f"\"\"\"{content_text}\"\"\"\n\n"
                    f"Identify claims, assign claim_type, risk_level ('critical', 'high', 'medium', 'low'), and brief explanation."
                )
                system_prompt = "Strict insurance claims identification engine. Return valid JSON only."

                llm_claims: ClaimsExtractionResponse = llm_provider.generate_structured(
                    prompt=prompt,
                    schema=ClaimsExtractionResponse,
                    system_instruction=system_prompt
                )

                if llm_claims and llm_claims.claims:
                    for c in llm_claims.claims:
                        if c.claim_text.lower() not in seen_texts:
                            seen_texts.add(c.claim_text.lower())
                            extracted_claims.append(c)
            except Exception as e:
                logger.warning(f"Groq semantic claim extraction fallback: {e}")

        # If no risky claims found, record baseline marketing statement
        if not extracted_claims:
            first_line = content_text.split("\n")[0][:100].strip()
            extracted_claims.append(
                ClaimItem(
                    claim_text=first_line or "General brand awareness marketing copy",
                    claim_type="general_marketing",
                    risk_level="low",
                    explanation="Standard informational marketing copy without detected statutory risk triggers."
                )
            )

        return extracted_claims

claim_extractor = ClaimExtractor()
