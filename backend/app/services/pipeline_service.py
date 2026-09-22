import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.models.entities import ContentQueue
from app.database.session import SessionLocal
from app.schemas.agent_contracts import (
    ContentBrief,
    ContentSuiteRequest,
    ComplianceResult,
    GeneratedVariation
)
from app.services.research_service import research_service
from app.services.lessons_service import lessons_service
from app.services.content_service import content_service
from app.services.compliance_service import compliance_service
from app.services.localization_service import localization_service

logger = logging.getLogger("ja_assure.pipeline")

class PipelineService:
    """
    Central Orchestration Engine ("The Brain").
    Coordinates Research -> Lessons Retrieval -> Multi-Platform Generation -> Localization -> Compliance Gate -> Queue Insertion.
    Enforces MANDATORY Human Review: No item is ever automatically marked as 'approved' or 'published'.
    """

    async def process_content_pipeline(
        self,
        brand: str,
        topic: str,
        platform: str,
        content_type: str = "post",
        language: str = "en",
        key_benefits: Optional[List[str]] = None,
        target_persona: Optional[str] = None,
        cta: Optional[str] = None
    ) -> List[ContentQueue]:
        """
        Runs the full end-to-end pipeline for a specific brand, platform, and language:
        1. Contextual research
        2. Active lessons retrieval
        3. Content generation (A/B variations)
        4. Localization if target language != en
        5. Compliance verification
        6. Persisting to ContentQueue in 'human_review' (or 'pending') state.
        """
        brand_clean = brand.lower()
        platform_clean = platform.lower()
        lang_clean = language.lower()

        logger.info(f"[The Brain] Processing content pipeline: {brand_clean} | {platform_clean} | {lang_clean} | Topic: {topic}")

        # Step 1: Research Context
        research = await research_service.conduct_research(brand=brand_clean, topic=topic)

        # Step 2: Retrieve Relevant Lessons
        lessons = lessons_service.get_relevant_lessons_for_prompt(brand=brand_clean, platform=platform_clean)

        # Step 3: Content Generation (Variations A and B)
        brief = ContentBrief(
            brand=brand_clean,
            platform=platform_clean,
            content_type=content_type,
            topic=topic,
            target_persona=target_persona,
            key_benefits=key_benefits or research.recommended_angles,
            cta=cta,
            language="en", # generate base English first
            variations_count=2,
            context_lessons=lessons
        )
        variations = await content_service.generate_variations(brief)

        db = SessionLocal()
        created_records: List[ContentQueue] = []
        try:
            for var in variations:
                content_text = var.content_text

                # Step 4: Localization if requested
                if lang_clean != "en":
                    loc_res = await localization_service.localize_content(
                        text=content_text,
                        target_lang=lang_clean,
                        brand=brand_clean,
                        source_lang="en"
                    )
                    content_text = loc_res.localized_text

                # Step 5: Compliance Gate
                compliance = await compliance_service.evaluate_content(
                    brand=brand_clean,
                    content_text=content_text,
                    content_type=content_type,
                    platform=platform_clean,
                    language=lang_clean
                )

                # Step 6: Queue Contract
                # Even if compliance passes (score >= 85), human review is MANDATORY.
                # Content enters 'human_review' if compliance passed, or 'pending' / 'flagged' if compliance flagged issues.
                compliance_status = "passed" if compliance.passed else "flagged"
                queue_status = "human_review" if compliance.passed else "pending"

                metadata = {
                    "source_brief_topic": topic,
                    "headline": var.headline,
                    "hashtags": var.hashtags,
                    "cta": var.cta,
                    "media_prompt": var.media_prompt,
                    "compliance_status": compliance.status,
                    "compliance_score": compliance.score,
                    "compliance_jurisdiction": compliance.jurisdiction,
                    "compliance_product": compliance.product,
                    "compliance_disclaimer_status": compliance.disclaimer_status,
                    "compliance_violations": [v.model_dump() for v in compliance.violations],
                    "compliance_warnings": [w.model_dump() for w in compliance.warnings],
                    "compliance_suggestions": compliance.suggestions,
                    "disclaimers_required": compliance.disclaimers_required,
                    "claims_analyzed": [c.model_dump() for c in compliance.claims_analyzed],
                    "applied_lessons_count": len(lessons),
                    "pipeline_timestamp": datetime.now(timezone.utc).isoformat()
                }

                item = ContentQueue(
                    brand=brand_clean,
                    platform=platform_clean,
                    content_type=content_type,
                    topic=topic,
                    content_raw=content_text,
                    original_content_raw=content_text,  # immutable snapshot of the AI output as first generated
                    variation=var.variation_label,
                    language=lang_clean,
                    compliance_status=compliance_status,
                    status=queue_status, # NEVER 'approved'
                    compliance_score=compliance.score,
                    reason_tag=compliance.violations[0].rule_id if compliance.violations else None,
                    notes=compliance.overall_feedback,
                    metadata_json=json.dumps(metadata)
                )
                db.add(item)
                db.commit()
                db.refresh(item)
                created_records.append(item)

            return created_records
        except Exception as e:
            db.rollback()
            logger.error(f"Pipeline execution error: {e}")
            raise e
        finally:
            db.close()

    async def run_sequential_campaign(
        self,
        brand: str,
        topic: str,
        platform: str = "linkedin",
        content_type: str = "post",
        language: str = "en",
        key_benefits: Optional[List[str]] = None,
        target_persona: Optional[str] = None,
        cta: Optional[str] = None,
        include_media: bool = False,
        media_format: str = "auto",
        target_duration: int = 45,
    ) -> ContentQueue:
        """
        One sequential call -- research -> lessons -> content generation ->
        (optional real image/video generation) -> compliance -> ContentQueue --
        instead of a caller making separate /content/generate,
        /content/video, and /content/video/enqueue calls by hand.

        Always produces exactly ONE ContentQueue row (not an A/B pair): real
        media generation is too expensive to run per variation. Use
        /content/suite for a pure-text A/B batch instead.

        Lands in 'human_review' (or 'pending' if compliance flagged it) --
        NEVER auto-approved, NEVER auto-published. This mirrors
        process_content_pipeline exactly; it does not introduce a second,
        less-governed path to the queue.
        """
        brand_clean = brand.lower()
        platform_clean = platform.lower()
        lang_clean = language.lower()

        logger.info(f"[Sequential Campaign] {brand_clean} | {platform_clean} | media={include_media} | Topic: {topic}")

        research = await research_service.conduct_research(brand=brand_clean, topic=topic)
        lessons = lessons_service.get_relevant_lessons_for_prompt(brand=brand_clean, platform=platform_clean)

        brief = ContentBrief(
            brand=brand_clean, platform=platform_clean, content_type=content_type, topic=topic,
            target_persona=target_persona, key_benefits=key_benefits or research.recommended_angles,
            cta=cta, language="en", variations_count=1, context_lessons=lessons,
        )
        variations = await content_service.generate_variations(brief)
        var = variations[0]
        content_text = var.content_text

        if lang_clean != "en":
            loc_res = await localization_service.localize_content(
                text=content_text, target_lang=lang_clean, brand=brand_clean, source_lang="en",
            )
            content_text = loc_res.localized_text

        media_result = None
        effective_content_type = content_type
        if include_media:
            from app.services.media_decision_engine import decide_and_generate_media
            media_result = await decide_and_generate_media(
                brand=brand_clean, topic=topic, format_type=media_format,
                target_duration=target_duration, platform=platform_clean, language=lang_clean,
            )
            if media_result.media_path and media_result.media_type == "video":
                effective_content_type = "reel"

        compliance = await compliance_service.evaluate_content(
            brand=brand_clean, content_text=content_text, content_type=effective_content_type,
            platform=platform_clean, language=lang_clean,
        )
        compliance_status = "passed" if compliance.passed else "flagged"
        queue_status = "human_review" if compliance.passed else "pending"

        metadata = {
            "source_brief_topic": topic,
            "headline": var.headline,
            "hashtags": var.hashtags,
            "cta": var.cta,
            "media_prompt": var.media_prompt,
            "compliance_status": compliance.status,
            "compliance_score": compliance.score,
            "compliance_jurisdiction": compliance.jurisdiction,
            "compliance_product": compliance.product,
            "compliance_disclaimer_status": compliance.disclaimer_status,
            "compliance_violations": [v.model_dump() for v in compliance.violations],
            "compliance_warnings": [w.model_dump() for w in compliance.warnings],
            "compliance_suggestions": compliance.suggestions,
            "disclaimers_required": compliance.disclaimers_required,
            "claims_analyzed": [c.model_dump() for c in compliance.claims_analyzed],
            "applied_lessons_count": len(lessons),
            "pipeline_timestamp": datetime.now(timezone.utc).isoformat(),
            "sequential_campaign": True,
        }
        if media_result is not None:
            metadata["media_type"] = media_result.media_type
            metadata["media_source"] = media_result.source
            metadata["media_is_real_ai"] = media_result.is_real_ai
            metadata["media_error"] = media_result.error
            if media_result.media_path:
                if media_result.media_type == "video":
                    metadata["video_path"] = str(media_result.media_path)
                    metadata["video_url"] = media_result.media_url
                    metadata["video_duration_seconds"] = media_result.duration_seconds
                    metadata["ai_generated_scene_count"] = media_result.ai_generated_scene_count
                    metadata["fallback_scene_count"] = media_result.fallback_scene_count
                else:
                    metadata["image_path"] = str(media_result.media_path)
                    metadata["image_url"] = media_result.media_url

        db = SessionLocal()
        try:
            item = ContentQueue(
                brand=brand_clean, platform=platform_clean, content_type=effective_content_type,
                topic=topic, content_raw=content_text, original_content_raw=content_text,
                variation=var.variation_label, language=lang_clean,
                compliance_status=compliance_status, status=queue_status,  # NEVER 'approved'
                compliance_score=compliance.score,
                reason_tag=compliance.violations[0].rule_id if compliance.violations else None,
                notes=compliance.overall_feedback,
                metadata_json=json.dumps(metadata),
            )
            db.add(item)
            db.commit()
            db.refresh(item)
            return item
        except Exception as e:
            db.rollback()
            logger.error(f"Sequential campaign execution error: {e}")
            raise e
        finally:
            db.close()

    async def generate_content_suite(self, suite_req: ContentSuiteRequest) -> List[ContentQueue]:
        """
        Batch suite generation across multiple platforms, content types, and languages.
        """
        all_created: List[ContentQueue] = []
        for platform in suite_req.platforms:
            for content_type in suite_req.content_types:
                for lang in suite_req.languages:
                    items = await self.process_content_pipeline(
                        brand=suite_req.brand,
                        topic=suite_req.topic,
                        platform=platform,
                        content_type=content_type,
                        language=lang,
                        key_benefits=suite_req.key_benefits
                    )
                    all_created.extend(items)
        return all_created

pipeline_service = PipelineService()
