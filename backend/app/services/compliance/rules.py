import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class ComplianceRule:
    rule_id: str
    name: str
    category: str
    severity: str # CRITICAL, HIGH, MEDIUM, LOW
    penalty: float
    description: str
    patterns: List[str] = field(default_factory=list)
    explanation: str = ""
    suggested_fix: str = ""
    is_absence_rule: bool = False
    brand_filter: Optional[str] = None
    product_filter: Optional[str] = None
    jurisdiction_filter: Optional[str] = None

    def evaluate(self, text: str, brand: Optional[str] = None, jurisdiction: Optional[str] = None) -> Optional[Dict[str, Any]]:
        # Filter checks
        if self.brand_filter and brand and brand.lower() != self.brand_filter.lower():
            return None
        if self.jurisdiction_filter and jurisdiction and jurisdiction.lower() != self.jurisdiction_filter.lower():
            return None

        # Absence rule (e.g. disclaimer check)
        if self.is_absence_rule:
            found = any(re.search(pat, text, re.IGNORECASE) for pat in self.patterns)
            if not found:
                return {
                    "rule_id": self.rule_id,
                    "category": self.category,
                    "severity": self.severity,
                    "penalty": self.penalty,
                    "matched_text": "Missing statutory intermediary disclaimer",
                    "reason": self.explanation,
                    "recommendation": self.suggested_fix
                }
            return None

        # Positive pattern matching
        for pat in self.patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                matched_str = match.group(0).strip()
                return {
                    "rule_id": self.rule_id,
                    "category": self.category,
                    "severity": self.severity,
                    "penalty": self.penalty,
                    "matched_text": matched_str,
                    "reason": f"{self.name}: {self.explanation}",
                    "recommendation": self.suggested_fix
                }

        return None


# 12 Core Extensible Regulatory Compliance Rules
COMPLIANCE_RULES_REGISTRY: List[ComplianceRule] = [
    # A. Guaranteed Outcomes
    ComplianceRule(
        rule_id="RULE-01-GUARANTEED-OUTCOME",
        name="Guaranteed Insurance Outcomes",
        category="GUARANTEED_OUTCOME",
        severity="CRITICAL",
        penalty=35.0,
        description="Prohibits unconditional guarantee claims that misrepresent policy terms and conditions.",
        patterns=[
            r"\b100%\s*(guaranteed|risk[\s-]free|protection|covered|payout)\b",
            r"\bguaranteed\s*(payout|claim|approval|replacement|recovery|compensation|coverage|protection)\b",
            r"\bzero\s*risk\b",
            r"\bnever\s*denied\b",
            r"\brisk[\s-]free\s*(protection|coverage|policy)\b"
        ],
        explanation="Insurance regulations strictly prohibit absolute guarantee claims without underwriting conditions.",
        suggested_fix="Replace absolute guarantee claims with 'Comprehensive protection subject to policy underwriting criteria'."
    ),

    # B. Unsupported Coverage
    ComplianceRule(
        rule_id="RULE-02-UNSUPPORTED-COVERAGE",
        name="Unsupported Universal Coverage Claims",
        category="UNSUPPORTED_COVERAGE",
        severity="CRITICAL",
        penalty=30.0,
        description="Prohibits claims that policy covers every scenario, loss, or total immunity.",
        patterns=[
            r"\bcovers?\s*(everything|all\s*losses?|anything|every\s*situation|all\s*damages?|every\s*possible\s*loss)\b",
            r"\bunlimited\s*(coverage|protection|indemnity|limits?)\b",
            r"\bcomplete\s*immunity\b",
            r"\bnever\s*pay\s*out\s*of\s*pocket\b",
            r"\ball[\s-]inclusive\s*zero[\s-]exclusion\b",
            r"\bzero\s*exclusions?\b",
            r"\buniversal\s*coverage\b"
        ],
        explanation="Claiming unlimited or all-inclusive coverage misrepresents policy exclusions, sub-limits, and statutory parameters.",
        suggested_fix="Specify exact agreed-value coverage parameters and note that terms, limits, and policy exclusions apply."
    ),

    # C. Misleading / Absolute Claims
    ComplianceRule(
        rule_id="RULE-03-MISLEADING-ABSOLUTE",
        name="Misleading Absolute Protection Claims",
        category="MISLEADING_ABSOLUTE_CLAIM",
        severity="HIGH",
        penalty=25.0,
        description="Flags absolute marketing claims creating false consumer certainty.",
        patterns=[
            r"\bcomplete\s*protection\s*from\s*all\b",
            r"\btotal\s*peace\s*of\s*mind\s*guaranteed\b",
            r"\bnever\s*worry\s*about\s*any\s*(loss|claim|lawsuit)\b",
            r"\bflawless\s*coverage\b"
        ],
        explanation="Absolute marketing language creates an expectation of immunity that violates insurance fair conduct rules.",
        suggested_fix="Frame benefits around risk mitigation and specialized policy limits rather than absolute immunity."
    ),

    # D. Unsupported Comparative Claims
    ComplianceRule(
        rule_id="RULE-04-UNSUPPORTED-COMPARATIVE",
        name="Unsupported Comparative Marketing",
        category="UNSUPPORTED_COMPARATIVE_CLAIM",
        severity="MEDIUM",
        penalty=15.0,
        description="Detects unsubstantiated superiority claims over other insurers without cited survey benchmarks.",
        patterns=[
            r"\bbetter\s*than\s*(all\s*other|any\s*other)\s*(insurers?|brokers?|policies?)\b",
            r"\bthe\s*best\s*insurer\s*in\s*(asia|singapore|malaysia|the\s*world)\b",
            r"\bnumber\s*one\s*(broker|insurer|provider)\b",
            r"\bunmatched\s*by\s*anyone\b"
        ],
        explanation="Superlative comparative claims without verifiable third-party survey citations breach advertising standards.",
        suggested_fix="Highlight JA Assure's bespoke features objectively (e.g. 'Specialized agreed-value underwriting') without unvetted superlative ranks."
    ),

    # E. Unsupported Pricing Claims
    ComplianceRule(
        rule_id="RULE-05-UNSUPPORTED-PRICING",
        name="Unsubstantiated Pricing Superlatives",
        category="UNSUPPORTED_PRICING_CLAIM",
        severity="MEDIUM",
        penalty=15.0,
        description="Detects unverified price guarantees, lowest rate superlatives, and misleading discounts.",
        patterns=[
            r"\bcheapest\s*(in\s*the\s*country|in\s*asia|insurance|rates?|premiums?|in\s*singapore|coverage|policy|jewellery\s*insurance)?\b",
            r"\b(absolute\s*)?lowest\s*(rates?|premiums?|prices?)\s*(anywhere|guaranteed)?\b",
            r"\bunbeatable\s*premiums?\b",
            r"\bcut\s*your\s*premiums?\s*in\s*half\s*guaranteed\b"
        ],
        explanation="Pricing superlatives without comparative independent actuarial data violate fair competition standards.",
        suggested_fix="Use 'Competitive, tailored specialist premium rates' instead of claiming lowest or cheapest rates."
    ),

    # F. Missing / Incorrect Disclaimers
    ComplianceRule(
        rule_id="RULE-06-MISSING-DISCLAIMER",
        name="Missing Statutory Intermediary Disclaimer",
        category="MISSING_DISCLAIMER",
        severity="HIGH",
        penalty=20.0,
        is_absence_rule=True,
        description="Enforces mandatory statutory intermediary disclosures across Southeast Asian jurisdictions.",
        patterns=[
            r"terms\s*(and|&|,)\s*conditions",
            r"terms\s*apply",
            r"subject\s*to\s*underwriting",
            r"underwritten\s*by",
            r"licensed\s*(partner\s*)?insurers?",
            r"terma\s*dan\s*syarat",
            r"syarat\s*dan\s*ketentuan",
            r"条款",
            r"เงื่อนไข"
        ],
        explanation="Licensed insurance marketing mandates statutory disclosures indicating terms, conditions, and underwriting limits apply.",
        suggested_fix="Append: '*Terms, conditions, and underwriting limits apply. JA Assure is a registered corporate insurance intermediary.*'"
    ),

    # G. Medical Advice / Diagnosis / Treatment Claims (DoctorShield)
    ComplianceRule(
        rule_id="RULE-07-MEDICAL-ADVICE",
        name="Prohibited Medical Advice or Diagnosis Claims",
        category="MEDICAL_ADVICE_DIAGNOSIS",
        severity="CRITICAL",
        penalty=35.0,
        brand_filter="doctorshield",
        description="Strictly prevents clinical medical advice, diagnostic recommendations, or treatment guarantees in indemnity copy.",
        patterns=[
            r"\bdiagnos(e|is|ing|es)\b",
            r"\btreat(ment)?\s*(protocols?|guidelines?|cures?)\b",
            r"\bcure\s*patients?\b",
            r"\bprescribes?\s*(clinical|medical|medication|treatments?|negligence|recovery|protocols?)?\b",
            r"\bclinical\s*(error|negligence|diagnosis|treatment|advice|outcome)\b",
            r"\bguaranteed\s*patient\s*recovery\b"
        ],
        explanation="DoctorShield is an indemnity policy protecting medical practitioners from liability. It must never offer patient diagnosis or clinical treatment advice.",
        suggested_fix="Confine copy strictly to medico-legal defence counsel, retroactive indemnity liability limits, and practice protection."
    ),

    # H. Unsupported Statistics
    ComplianceRule(
        rule_id="RULE-08-UNSUPPORTED-STATISTICS",
        name="Unsourced Quantitative Statistical Claims",
        category="UNSUPPORTED_STATISTICS",
        severity="MEDIUM",
        penalty=15.0,
        description="Flags specific percentage or statistical claims lacking source citations.",
        patterns=[
            r"\b(99(\.9)?%|98%|95%|\d{2,3}(\.\d+)?%)\s*(of\s*(all\s*)?(our\s*)?(clients?|jewellers?|doctors?|policyholders?|claims?)|save\b|customer\s*satisfaction|payout\s*rate)\b",
            r"\btrusted\s*by\s*(100%|all)\s*(doctors|jewellers|couriers)\b",
            r"\bproven\s*to\s*cut\s*losses\s*by\s*\d+%\b"
        ],
        explanation="Publishing precise quantitative payout rates or market statistics without verifiable citations is deemed misleading advertising.",
        suggested_fix="Cite official audited claims metrics or state 'Consistently high claims settlement track record based on historical underwriting data'."
    ),

    # I. Competitor Disparagement
    ComplianceRule(
        rule_id="RULE-09-COMPETITOR-DISPARAGEMENT",
        name="Misleading or Disparaging Competitor Claims",
        category="COMPETITOR_DISPARAGEMENT",
        severity="HIGH",
        penalty=25.0,
        description="Prohibits direct disparagement or deceptive comparative statements against competitor brokers/insurers.",
        patterns=[
            r"\bbetter\s*than\s*(competitors?|singmed|briteprotect|cargosafe|standard\s*brokers?)\b",
            r"\bdon['']t\s*trust\s*other\s*(insurers?|brokers?)\b",
            r"\b(competitors?|other\s*(brokers?|insurers?))\s*.*?(fraudulent|scam|cheat|deceive|fail\s*you|rip\s*you\s*off|deny|denies|denying|reject)",
            r"\bcompetitors?\s*refuse\s*to\s*pay\b"
        ],
        explanation="Direct disparagement or unverified negative claims about competitor policies breach regulatory codes of advertising conduct.",
        suggested_fix="Highlight JA Assure's strengths objectively without derogatory or unverified references to competitor entities."
    ),

    # J. False Certainty
    ComplianceRule(
        rule_id="RULE-10-FALSE-CERTAINTY",
        name="Claims Implying Absence of Due Diligence / Investigation",
        category="FALSE_CERTAINTY",
        severity="HIGH",
        penalty=20.0,
        description="Detects promises suggesting claims are settled without standard documentation, assessment, or investigation.",
        patterns=[
            r"\bno\s*questions?\s*asked\b",
            r"\bno\s*investigation\s*needed\b",
            r"\binstant\s*cash\s*payout\s*on\s*the\s*spot\b",
            r"\bno\s*paperwork\s*or\s*assessment\b",
            r"\bno\s*underwriting\s*required\b"
        ],
        explanation="All insurance claims require statutory verification and evidence. Promising 'no questions asked' payouts contradicts insurance contract law.",
        suggested_fix="Use 'Streamlined appraisal verification and expedited claim advisory' instead of claiming zero questions or no investigation."
    ),

    # K. Automatic Payout / Approval Promises
    ComplianceRule(
        rule_id="RULE-11-AUTOMATIC-PAYOUT",
        name="Unconditional Automatic Payout Promises",
        category="AUTOMATIC_PAYOUT_APPROVAL",
        severity="CRITICAL",
        penalty=35.0,
        description="Flags promises stating payouts or policy issuance are automatically approved without assessment.",
        patterns=[
            r"\binstant\s*(automatic\s*)?(approval|payout|claim|settlement)\b",
            r"\bautomatic(ally)?\s*(paid|approved|issued|settled|disbursed)\b",
            r"\bevery\s*claim\s*is\s*automatically\s*honoured\b",
            r"\bguaranteed\s*immediate\s*settlement\b"
        ],
        explanation="Promising automatic claim approval disregards standard policy exclusion reviews and fraud prevention obligations.",
        suggested_fix="State that claims are assessed swiftly under agreed-value policy conditions."
    ),

    # L. Product Mismatch
    ComplianceRule(
        rule_id="RULE-12-PRODUCT-MISMATCH",
        name="Universal Eligibility / Inappropriate Product Scope",
        category="PRODUCT_MISMATCH",
        severity="HIGH",
        penalty=25.0,
        description="Flags claims asserting that all entities/practitioners are universally covered regardless of specialty, or misrepresenting product scope.",
        patterns=[
            r"\bevery\s*(doctor|surgeon|practitioner)\s*is\s*(automatically\s*)?covered\b",
            r"\bcovers\s*every\s*type\s*of\s*business\s*with\s*no\s*restrictions\b",
            r"\ball\s*cargo\s*is\s*automatically\s*eligible\b",
            r"\bno\s*matter\s*what\s*your\s*medical\s*specialty\s*or\s*history\b"
        ],
        explanation="Insurance products are strictly underwritten based on specialty risk profile, cargo classification, and prior claims history.",
        suggested_fix="Clarify that coverage eligibility is subject to individual risk profiling and underwriting acceptance."
    )
]

# Legacy alias list for backward-compatibility with existing tests and /rules endpoint
COMPLIANCE_RULES: List[Dict[str, Any]] = [
    {
        "id": r.rule_id,
        "name": r.name,
        "category": r.category,
        "severity": r.severity.lower(),
        "penalty": r.penalty,
        "explanation": r.explanation,
        "suggested_fix": r.suggested_fix,
        "patterns": r.patterns,
        "is_absence_rule": r.is_absence_rule,
        "brand_filter": r.brand_filter
    }
    for r in COMPLIANCE_RULES_REGISTRY
]

ComplianceRuleRegistry = COMPLIANCE_RULES_REGISTRY
