"""
Project 2 ("The Hands") background publishing worker.

Reuses 100% of publishing_service.publish_to_linkedin()'s existing logic (HITL
gate, idempotency, retry/backoff, immutable per-attempt PublishingRecord audit
trail) -- this module is purely the polling/selection wrapper around it, never a
second publishing implementation.

Two ways to run it, both reusing the exact same run_once():
1. POST /publishing/worker/run-once -- one manual, human-triggered pass.
2. Automatic background polling (run_forever), started from app.main's lifespan
   ONLY when PUBLISH_WORKER_ENABLED=true (default: false). Simply starting the
   app never begins automatic publishing -- this is an explicit operator opt-in,
   since a worker that autonomously posts to a real, public LinkedIn feed is a
   materially different risk than every other action in this codebase. Whether
   run manually or automatically, human approval (status=="approved" AND
   compliance_status=="passed") remains the absolute, unbypassable gate.
"""
import asyncio
import logging
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import SessionLocal
from app.models.entities import ContentQueue, PublishingRecord
from app.services import publishing_service
from app.services.publishing_service import PublishingGateError, DuplicatePublishError

logger = logging.getLogger("ja_assure.publishing.worker")


def find_eligible_content(db: Session, platform: str = "linkedin", limit: int = 10) -> List[ContentQueue]:
    """
    Content that is approved + compliance-passed + not already successfully
    published to this platform. Mirrors hitl_service.is_publishable() plus the
    same idempotency check publish_to_linkedin() itself enforces -- filtered here
    too so the worker's own logs/summary don't even attempt already-published
    items, though publish_to_linkedin() would safely reject them anyway.
    """
    query = (
        select(ContentQueue)
        .where(ContentQueue.status == "approved", ContentQueue.compliance_status == "passed")
        .limit(limit)
    )
    candidates = db.execute(query).scalars().all()

    eligible = []
    for content in candidates:
        already_published = (
            db.query(PublishingRecord)
            .filter(
                PublishingRecord.content_id == content.id,
                PublishingRecord.platform == platform,
                PublishingRecord.status == "published",
            )
            .first()
        )
        if not already_published:
            eligible.append(content)
    return eligible


async def run_once(max_items: int = 10) -> List[Dict[str, Any]]:
    """
    Runs exactly one polling pass: finds eligible content, publishes each through
    the existing gated service, and returns a summary. Never publishes unapproved
    content -- eligibility is defined by the same is_publishable() rule as every
    other publishing path; there is no separate/looser rule for the worker.
    """
    db = SessionLocal()
    results: List[Dict[str, Any]] = []
    try:
        eligible = find_eligible_content(db, limit=max_items)
        logger.info(f"[publishing_worker] Found {len(eligible)} eligible content item(s) to publish.")

        for content in eligible:
            try:
                record = await publishing_service.publish_to_linkedin(db, content.id)
                results.append({
                    "content_id": content.id,
                    "status": record.status,
                    "external_post_id": record.external_post_id,
                    "error_info": record.error_info,
                })
            except (PublishingGateError, DuplicatePublishError) as e:
                # Content became ineligible between selection and dispatch (e.g. a
                # concurrent request already published it) -- log and move on,
                # never raise and abort the rest of the batch.
                logger.info(f"[publishing_worker] content #{content.id} skipped: {e.message}")
                results.append({"content_id": content.id, "status": "skipped", "reason": e.message})
    finally:
        db.close()

    return results


async def run_forever(interval_seconds: int = None, max_items: int = 10) -> None:
    """
    Continuously polls at a fixed interval, calling run_once() each pass. Only
    ever invoked from app.main's lifespan when PUBLISH_WORKER_ENABLED=true -- see
    module docstring. A single pass raising is logged and swallowed so a transient
    error (e.g. a DB hiccup) doesn't kill the background task permanently.
    """
    interval = interval_seconds if interval_seconds is not None else settings.PUBLISH_WORKER_INTERVAL_SECONDS
    logger.info(f"[publishing_worker] Automatic background polling started (interval={interval}s).")
    try:
        while True:
            try:
                results = await run_once(max_items=max_items)
                if results:
                    logger.info(f"[publishing_worker] Background pass processed {len(results)} item(s).")
            except Exception as e:
                logger.error(f"[publishing_worker] Background pass failed unexpectedly: {e}")
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        logger.info("[publishing_worker] Automatic background polling stopped.")
        raise
