import re
import logging
from typing import Dict, Any, List, Optional
from app.schemas.agent_contracts import ComplianceViolation, ComplianceResult
from app.services.compliance.engine import compliance_engine
from app.services.compliance.context import resolve_context, ComplianceContext
from app.services.llm_provider import llm_provider

logger = logging.getLogger("ja_assure.compliance.rewriter")

class ComplianceRewriter:
    """
    Context-aware AI Compliance Rewrite Service.
    Sanitizes non-compliant copy while preserving marketing hook and brand voice.
    Mandates an INDEPENDENT RE-CHECK through the compliance engine.
    """

    async def rewrite_content(
        self,
        brand: Optional[str] = None,
        original_text: str = "",
        content_type: str = "post",
        product: Optional[str] = None,
        country: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        skip_llm: bool = False
    ) -> Dict[str, Any]:
        ctx: ComplianceContext = resolve_context(
            brand=brand,
            product=product,
            jurisdiction=jurisdiction,
            country=country,
            platform=platform,
            language=language,
            content_text=original_text
        )

        # 1. Initial Compliance Evaluation
        initial_eval: ComplianceResult = await compliance_engine.evaluate(
            brand=ctx.brand,
            content_text=original_text,
            content_type=content_type,
            product=ctx.product,
            jurisdiction=ctx.jurisdiction,
            platform=ctx.platform,
            language=ctx.language,
            skip_llm=True
        )

        violations_summary = "\n".join([
            f"- [{v.severity}] {v.rule_id} ({v.category}): {v.reason} (Flagged phrase: '{v.matched_text}') -> Recommendation: {v.recommendation}"
            for v in initial_eval.violations
        ]) if initial_eval.violations else "No violations flagged."

        # 2. Synthesize Compliant Copy (Groq AI or Deterministic Fallback)
        if not skip_llm:
            try:
                system_prompt = (
                    f"You are the Senior Compliance Editor for JA Assure ({ctx.brand.title()}) in {ctx.jurisdiction}. "
                    f"Rewrite marketing copy to achieve 100% regulatory compliance while preserving persuasive marketing impact."
                )
                prompt = (
                    f"Rewrite the following marketing copy to be fully compliant under {ctx.regulatory_framework}.\n\n"
                    f"ORIGINAL COPY:\n\"\"\"\n{original_text}\n\"\"\"\n\n"
                    f"FLAGGED REGULATORY RISKS TO REMOVE:\n{violations_summary}\n\n"
                    f"STRICT COMPLIANCE DIRECTIVES:\n"
                    f"1. Remove all unconditional guarantees (e.g. '100% guaranteed', 'zero risk', 'never denied', 'payout guaranteed').\n"
                    f"2. Replace universal coverage claims with 'Subject to policy underwriting criteria and agreed-value limits'.\n"
                    f"3. Strip all patient medical diagnosis or treatment advice for DoctorShield; focus strictly on legal defense & indemnity limits.\n"
                    f"4. Remove pricing superlatives ('cheapest rates', 'lowest in Singapore') and use 'competitive specialist rates'.\n"
                    f"5. Remove disparaging references to competitor brokers or insurers.\n"
                    f"6. MANDATORY DISCLAIMER TO APPEND AT THE END:\n{ctx.disclaimer}\n\n"
                    f"Return ONLY the rewritten, compliant copy text without meta-commentary."
                )

                corrected_text = self._generate_llm_rewrite(prompt, system_prompt)
            except Exception as e:
                logger.warning(f"Groq compliance rewrite fallback triggered: {e}")
                corrected_text = self._deterministic_rewrite(original_text, ctx, initial_eval.violations)
        else:
            corrected_text = self._deterministic_rewrite(original_text, ctx, initial_eval.violations)

        # Ensure disclaimer is appended
        if "terms" not in corrected_text.lower() and "syarat" not in corrected_text.lower() and "terma" not in corrected_text.lower():
            corrected_text = f"{corrected_text.strip()}\n\n{ctx.disclaimer}"

        # 3. MANDATORY INDEPENDENT RE-CHECK
        # We pass the newly generated copy through the exact same engine
        recheck_eval: ComplianceResult = await compliance_engine.evaluate(
            brand=ctx.brand,
            content_text=corrected_text,
            content_type=content_type,
            product=ctx.product,
            jurisdiction=ctx.jurisdiction,
            platform=ctx.platform,
            language=ctx.language,
            skip_llm=True
        )

        resolved_violations = [
            v.rule_id for v in initial_eval.violations 
            if not any(rv.rule_id == v.rule_id for rv in recheck_eval.violations)
        ]
        remaining_violations = [v.rule_id for v in recheck_eval.violations]

        return {
            "original_text": original_text,
            "corrected_text": corrected_text,
            "brand": ctx.brand,
            "product": ctx.product,
            "jurisdiction": ctx.jurisdiction,
            "previous_score": initial_eval.score,
            "new_score": recheck_eval.score,
            "previous_status": initial_eval.status,
            "new_status": recheck_eval.status,
            "previous_passed": initial_eval.passed,
            "new_passed": recheck_eval.passed,
            "recheck_passed": recheck_eval.passed,
            "resolved_violations": resolved_violations,
            "remaining_violations": remaining_violations,
            "remediation_actions": resolved_violations or ["sanitized_claims_and_appended_disclaimer"],
            "new_violations": [v.model_dump() for v in recheck_eval.violations],
            "recheck_result": recheck_eval.model_dump(),
            "human_review_required": True # MANDATORY: Never bypass human sign-off
        }

    def _generate_llm_rewrite(self, prompt: str, system_prompt: str) -> str:
        return llm_provider.generate_text(
            prompt=prompt,
            system_instruction=system_prompt
        )

    def _deterministic_rewrite(
        self,
        text: str,
        ctx: ComplianceContext,
        violations: List[ComplianceViolation]
    ) -> str:
        corrected = text

        # 1. Replace absolute guarantees
        corrected = re.sub(r"\b100%\s*(guaranteed|risk[\s-]free|protection|payout|covered)(\s*payout)?\b", "Comprehensive agreed-value protection", corrected, flags=re.IGNORECASE)
        corrected = re.sub(r"\bguaranteed\s*(payout|claim|approval|replacement|recovery)\b", "Underwritten agreed-value settlement", corrected, flags=re.IGNORECASE)
        corrected = re.sub(r"\bzero\s*risk\b", "mitigated exposure", corrected, flags=re.IGNORECASE)
        corrected = re.sub(r"\bnever\s*denied\b", "transparent claims adjudication", corrected, flags=re.IGNORECASE)
        corrected = re.sub(r"\bno\s*questions?\s*asked\b", "streamlined appraisal verification", corrected, flags=re.IGNORECASE)
        corrected = re.sub(r"\bautomatic(ally)?\s*(paid|approved|issued|settled)\b", "efficiently assessed under policy terms", corrected, flags=re.IGNORECASE)

        # 2. Universal coverage claims
        corrected = re.sub(r"\bcovers?\s*(everything|all\s*losses?|anything|every\s*situation|all\s*damages?|every\s*possible\s*loss)\b", "covers scheduled policy perils", corrected, flags=re.IGNORECASE)
        corrected = re.sub(r"\bunlimited\s*(coverage|protection|liability)\b", "tailored liability limits", corrected, flags=re.IGNORECASE)
        corrected = re.sub(r"\bzero\s*exclusions?\b", "defined policy terms", corrected, flags=re.IGNORECASE)
        corrected = re.sub(r"\buniversal\s*coverage\b", "comprehensive scheduled perils protection", corrected, flags=re.IGNORECASE)
        corrected = re.sub(r"\bevery\s*(doctor|surgeon|practitioner)\s*is\s*(automatically\s*)?covered\b", "qualifying specialists can apply for bespoke cover", corrected, flags=re.IGNORECASE)

        # 3. Superlative pricing & comparisons
        corrected = re.sub(r"\bcheapest\s*(in\s*the\s*country|in\s*asia|rates?|premiums?|in\s*singapore)\b", "competitive specialist rates", corrected, flags=re.IGNORECASE)
        corrected = re.sub(r"\blowest\s*(rates?|premiums?|prices?)\s*(guaranteed)?\b", "tailored premium structures", corrected, flags=re.IGNORECASE)
        corrected = re.sub(r"\bbetter\s*than\s*(all\s*other|competitors?|singmed|briteprotect)\b", "distinctive bespoke underwriting", corrected, flags=re.IGNORECASE)

        # 4. DoctorShield medical advice stripping
        if ctx.brand == "doctorshield":
            corrected = re.sub(r"\bdiagnos(e|is|ing)\b", "practice consultation", corrected, flags=re.IGNORECASE)
            corrected = re.sub(r"\btreat(ment)?\s*(protocols?|guidelines?|cures?)\b", "medico-legal compliance protocols", corrected, flags=re.IGNORECASE)
            corrected = re.sub(r"\bprescribe\s*(medication|treatments?)\b", "consult with panel legal advisors", corrected, flags=re.IGNORECASE)
            corrected = re.sub(r"\bcure\s*patients?\b", "manage clinical risk", corrected, flags=re.IGNORECASE)

        # 5. Append context-aware statutory disclaimer
        if not re.search(r"terms\s*(and|&|,)\s*conditions", corrected, re.IGNORECASE) and not re.search(r"syarat\s*dan\s*ketentuan", corrected, re.IGNORECASE):
            corrected = f"{corrected.strip()}\n\n{ctx.disclaimer}"

        return corrected

compliance_rewriter = ComplianceRewriter()
