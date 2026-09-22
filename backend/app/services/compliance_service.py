import logging
from typing import Dict, Any, List, Optional
from app.schemas.agent_contracts import ComplianceResult, ComplianceViolation
from app.services.compliance.rules import COMPLIANCE_RULES, COMPLIANCE_RULES_REGISTRY
from app.services.compliance.engine import compliance_engine
from app.services.compliance.rewriter import compliance_rewriter
from app.services.compliance.context import resolve_context

logger = logging.getLogger("ja_assure.compliance")

class ComplianceService:
    """
    Unified Insurance Compliance Gate Facade.
    Provides context-aware evaluation, 12-rule deterministic scanning, Groq AI semantic review,
    explainable scoring, and compliance rewrite with mandatory independent recheck.
    """

    async def evaluate_content(
        self,
        brand: str,
        content_text: str,
        content_type: str = "post",
        product: Optional[str] = None,
        country: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        skip_llm: bool = False
    ) -> ComplianceResult:
        """
        Evaluate marketing copy against insurance regulatory rubrics across Southeast Asia.
        """
        return await compliance_engine.evaluate(
            brand=brand,
            content_text=content_text,
            content_type=content_type,
            product=product,
            country=country,
            jurisdiction=jurisdiction,
            platform=platform,
            language=language,
            skip_llm=skip_llm
        )

    engine = compliance_engine
    rewriter = compliance_rewriter

    async def rewrite_non_compliant_content(
        self,
        brand: str,
        original_text: str,
        content_type: str = "post",
        product: Optional[str] = None,
        country: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        skip_llm: bool = False
    ) -> Dict[str, Any]:
        """
        Compliance Rewrite Workflow:
        1. Evaluate original copy
        2. Rewrite to resolve violations while preserving marketing intent & brand voice
        3. Independently recheck the rewritten copy with the compliance gate
        4. Return before/after scores, resolved/remaining violations, and review state.
        """
        return await compliance_rewriter.rewrite_content(
            brand=brand,
            original_text=original_text,
            content_type=content_type,
            product=product,
            country=country,
            jurisdiction=jurisdiction,
            platform=platform,
            language=language,
            skip_llm=skip_llm
        )

    def evaluate_compliance(
        self,
        brand: str,
        content_text: str,
        content_type: str = "social_post",
        product: Optional[str] = None,
        country: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        skip_llm: bool = False
    ) -> ComplianceResult:
        """
        Synchronous/LangGraph compatible wrapper around evaluate_content.
        """
        import asyncio
        import concurrent.futures
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(
                    asyncio.run,
                    self.evaluate_content(
                        brand=brand,
                        content_text=content_text,
                        content_type=content_type,
                        product=product,
                        country=country,
                        jurisdiction=jurisdiction,
                        platform=platform,
                        language=language,
                        skip_llm=skip_llm
                    )
                ).result()
        else:
            return asyncio.run(
                self.evaluate_content(
                    brand=brand,
                    content_text=content_text,
                    content_type=content_type,
                    product=product,
                    country=country,
                    jurisdiction=jurisdiction,
                    platform=platform,
                    language=language,
                    skip_llm=skip_llm
                )
            )

# Singleton service instance
compliance_service = ComplianceService()

