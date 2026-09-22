import logging
from typing import List, Optional, Dict, Any
from app.schemas.agent_contracts import (
    ComplianceViolation,
    ComplianceResult,
    ClaimItem
)
from app.services.compliance.context import resolve_context, ComplianceContext
from app.services.compliance.rules import COMPLIANCE_RULES_REGISTRY, ComplianceRule
from app.services.compliance.claims import claim_extractor
from app.services.llm_provider import llm_provider

logger = logging.getLogger("ja_assure.compliance.engine")

class ComplianceEngine:
    """
    Unified Insurance Compliance Engine.
    Coordinates: Context Resolution -> Claim Extraction -> Deterministic Rules -> Groq AI Review -> Conflict Resolution -> Scoring.
    """

    async def evaluate(
        self,
        brand: Optional[str] = None,
        content_text: str = "",
        content_type: str = "post",
        product: Optional[str] = None,
        country: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        skip_llm: bool = False
    ) -> ComplianceResult:
        # Step 1: Context Resolution
        ctx: ComplianceContext = resolve_context(
            brand=brand,
            product=product,
            jurisdiction=jurisdiction,
            country=country,
            platform=platform,
            language=language,
            content_text=content_text
        )

        # Step 2: Claim Extraction
        claims: List[ClaimItem] = await claim_extractor.extract_claims(
            content_text=content_text,
            brand=ctx.brand,
            product=ctx.product,
            jurisdiction=ctx.jurisdiction,
            skip_llm=skip_llm
        )

        # Step 3: Deterministic Rule Evaluation
        deterministic_violations: List[ComplianceViolation] = []
        disclaimers_required: List[str] = []
        suggestions: List[str] = []
        disclaimer_status = "compliant"

        for rule in COMPLIANCE_RULES_REGISTRY:
            match_res = rule.evaluate(
                text=content_text,
                brand=ctx.brand,
                jurisdiction=ctx.jurisdiction
            )
            if match_res:
                violation = ComplianceViolation(
                    rule_id=match_res["rule_id"],
                    category=match_res["category"],
                    severity=match_res["severity"].upper(),
                    message=match_res["reason"],
                    reason=match_res["reason"],
                    flagged_phrase=match_res["matched_text"],
                    matched_text=match_res["matched_text"],
                    suggested_fix=match_res["recommendation"],
                    recommendation=match_res["recommendation"]
                )
                deterministic_violations.append(violation)
                suggestions.append(match_res["recommendation"])

                if rule.is_absence_rule:
                    disclaimer_status = "missing"
                    disclaimers_required.append(ctx.disclaimer)

        # Platform length constraint check (e.g. X / Twitter 280 chars)
        if ctx.platform == "x" and len(content_text) > 280:
            deterministic_violations.append(
                ComplianceViolation(
                    rule_id="RULE-11-PLATFORM-CONSTRAINT",
                    category="PLATFORM_CONSTRAINT",
                    severity="LOW",
                    message="X (Twitter) platform constraint exceeded: text is longer than 280 characters.",
                    reason=f"Content length is {len(content_text)} characters, exceeding the 280-character maximum for X.",
                    flagged_phrase=content_text[280:310],
                    matched_text=f"{len(content_text)} characters",
                    suggested_fix="Condense copy to under 280 characters to fit X format.",
                    recommendation="Shorten post text."
                )
            )

        # Step 4: Groq AI Semantic Review Layer
        llm_violations: List[ComplianceViolation] = []
        if not skip_llm and llm_provider.is_live and len(content_text.strip()) > 10:
            try:
                deterministic_summary = (
                    "\n".join([f"- {v.rule_id} ({v.severity}): {v.message}" for v in deterministic_violations])
                    if deterministic_violations else "No deterministic pattern violations detected."
                )

                prompt = (
                    f"You are the Chief Regulatory Insurance Compliance Auditor for JA Assure.\n"
                    f"Context:\n"
                    f"- Brand: {ctx.brand.title()}\n"
                    f"- Product: {ctx.product}\n"
                    f"- Jurisdiction: {ctx.jurisdiction} (Under authority: {ctx.regulatory_framework})\n"
                    f"- Platform: {ctx.platform.upper()}\n"
                    f"- Language: {ctx.language}\n\n"
                    f"MARKETING COPY TO AUDIT:\n"
                    f"\"\"\"\n{content_text}\n\"\"\"\n\n"
                    f"PRELIMINARY DETERMINISTIC FINDINGS:\n"
                    f"{deterministic_summary}\n\n"
                    f"CLAIMS EXTRACTED:\n"
                    f"{', '.join([c.claim_text for c in claims])}\n\n"
                    f"STRICT AUDIT GUIDELINES:\n"
                    f"1. Audit for misleading marketing, false certainty, unverified coverage, medical advice (DoctorShield), or pricing superlatives.\n"
                    f"2. Return severity as 'CRITICAL', 'HIGH', 'MEDIUM', or 'LOW'.\n"
                    f"3. Explain clear reasons and actionable recommendations.\n"
                    f"4. Do NOT invent fake legal statute numbers. Apply standard insurance fair-conduct principles.\n"
                    f"5. If compliant, set passed=true with empty violations."
                )

                llm_eval: ComplianceResult = llm_provider.generate_structured(
                    prompt=prompt,
                    schema=ComplianceResult,
                    system_instruction="Strict Insurance Compliance Auditor for Southeast Asia."
                )

                if llm_eval and llm_eval.violations:
                    for lv in llm_eval.violations:
                        # Normalize severity
                        sev_clean = (lv.severity or "medium").upper()
                        if sev_clean not in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                            sev_clean = "HIGH" if "crit" in sev_clean.lower() else "MEDIUM"
                        
                        llm_violations.append(
                            ComplianceViolation(
                                rule_id=lv.rule_id or "RULE-SEMANTIC-REVIEW",
                                category=lv.category or "SEMANTIC_REGULATORY_RISK",
                                severity=sev_clean,
                                message=lv.message or lv.reason or "Semantic regulatory concern identified by AI auditor",
                                reason=lv.reason or lv.message,
                                flagged_phrase=lv.flagged_phrase or lv.matched_text or "General copy nuance",
                                matched_text=lv.matched_text or lv.flagged_phrase,
                                suggested_fix=lv.suggested_fix or lv.recommendation or "Qualify claims with policy terms",
                                recommendation=lv.recommendation or lv.suggested_fix
                            )
                        )
            except Exception as e:
                logger.warning(f"Groq semantic compliance audit fallback: {e}")

        # Step 5: Deterministic + LLM Precedence & Conflict Resolution
        # RULE: Deterministic findings are authoritative. LLM cannot unflag deterministic violations.
        merged_violations: List[ComplianceViolation] = list(deterministic_violations)
        existing_rule_ids = {v.rule_id for v in deterministic_violations}

        for lv in llm_violations:
            # Add novel semantic violations discovered by LLM
            if lv.rule_id not in existing_rule_ids:
                merged_violations.append(lv)
                existing_rule_ids.add(lv.rule_id)
                if lv.recommendation and lv.recommendation not in suggestions:
                    suggestions.append(lv.recommendation)

        # Step 6: Explainable Deterministic Scoring
        score = 100.0
        has_critical = False
        has_high = False
        warnings_list: List[ComplianceViolation] = []
        actionable_violations: List[ComplianceViolation] = []

        for v in merged_violations:
            sev = (v.severity or "MEDIUM").upper()
            if sev == "CRITICAL":
                score -= 35.0
                has_critical = True
                actionable_violations.append(v)
            elif sev == "HIGH":
                score -= 25.0
                has_high = True
                actionable_violations.append(v)
            elif sev == "MEDIUM":
                score -= 15.0
                warnings_list.append(v)
                actionable_violations.append(v)
            else: # LOW / INFO
                score -= 10.0
                warnings_list.append(v)

        final_score = max(0.0, min(100.0, round(score, 1)))

        # Status determination:
        # CRITICAL violation OR score < 60.0 -> BLOCKED (cannot pass)
        # Score between 60.0 and 84.9 OR HIGH violation -> WARNING
        # Score >= 85.0 AND zero critical/high violations -> PASS
        if has_critical or final_score < 60.0:
            status = "BLOCKED"
            passed = False
        elif has_high or final_score < 85.0:
            status = "WARNING"
            passed = False
        else:
            status = "PASS"
            passed = True

        # Overall feedback synthesis
        if passed:
            overall_feedback = (
                f"Content passed insurance compliance screening for {ctx.jurisdiction} ({ctx.regulatory_framework}). "
                f"Score: {final_score}/100. No critical or high-risk violations detected. Mandatory human review required before dispatch."
            )
        elif status == "BLOCKED":
            overall_feedback = (
                f"Compliance gate BLOCKED this content ({len(actionable_violations)} violation(s), Score: {final_score}/100). "
                f"Contains critical regulatory risks (e.g. false guarantees or universal coverage claims). "
                f"Must undergo AI Compliance Rewrite or human revision before approval."
            )
        else:
            overall_feedback = (
                f"Compliance gate issued WARNINGS ({len(actionable_violations)} item(s), Score: {final_score}/100). "
                f"Requires remediation of disclaimers or comparative wording before human approval."
            )

        return ComplianceResult(
            passed=passed,
            score=final_score,
            status=status,
            violations=actionable_violations,
            warnings=warnings_list,
            suggestions=suggestions,
            overall_feedback=overall_feedback,
            disclaimers_required=disclaimers_required,
            disclaimer_status=disclaimer_status,
            claims_analyzed=claims,
            jurisdiction=ctx.jurisdiction,
            brand=ctx.brand,
            product=ctx.product,
            platform=ctx.platform,
            language=ctx.language,
            human_review_required=True # Mandatory human sign-off
        )

compliance_engine = ComplianceEngine()
