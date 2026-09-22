"""
Orchestrates a single LinkedIn publish attempt for one ContentQueue item.

This is the ONLY module allowed to call linkedin_client -- it enforces
hitl_service.is_publishable() before ever reaching LinkedIn, checks idempotency
(refuses to re-publish an already-published item), and retries transient failures
with bounded backoff while failing permanent errors immediately. Every attempt gets
its own immutable PublishingRecord row rather than overwriting prior history.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import ContentQueue, PublishingRecord
from app.services import hitl_service, linkedin_client
from app.services.linkedin_client import (
    LinkedInNotConfiguredError,
    LinkedInPermanentError,
    LinkedInTransientError,
)

logger = logging.getLogger("ja_assure.publishing")

PLATFORM = "linkedin"
MAX_ATTEMPTS = 3
BASE_BACKOFF_SECONDS = 2.0


class PublishingGateError(Exception):
    """Raised when the HITL/compliance gate rejects a publish request."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class DuplicatePublishError(Exception):
    """Raised when this content item is already published to this platform."""
    def __init__(self, message: str, existing_record: PublishingRecord):
        self.message = message
        self.existing_record = existing_record
        super().__init__(message)


def _already_published(db: Session, content_id: int) -> Optional[PublishingRecord]:
    query = (
        select(PublishingRecord)
        .where(
            PublishingRecord.content_id == content_id,
            PublishingRecord.platform == PLATFORM,
            PublishingRecord.status == "published",
        )
        .order_by(PublishingRecord.created_at.desc())
    )
    return db.execute(query).scalars().first()


def _extract_media(content: ContentQueue) -> Tuple[Optional[str], Optional[str]]:
    """Returns (image_path, video_path) from metadata_json, if present."""
    if not content.metadata_json:
        return None, None
    try:
        meta = json.loads(content.metadata_json)
    except (ValueError, TypeError):
        return None, None
    return meta.get("image_path") or meta.get("image_url"), meta.get("video_path") or meta.get("video_url")


async def publish_to_linkedin(
    db: Session,
    content_id: int,
    max_attempts: int = MAX_ATTEMPTS,
    backoff_seconds: float = BASE_BACKOFF_SECONDS,
) -> PublishingRecord:
    content = db.get(ContentQueue, content_id)
    if not content:
        raise ValueError(f"Content item #{content_id} not found")

    # Idempotency is checked BEFORE the HITL gate: a successful publish moves
    # content.status to "published", which is no longer "approved" -- checking the
    # gate first would then mask every duplicate attempt behind a misleading
    # "not approved" error instead of a clear duplicate response.
    existing = _already_published(db, content_id)
    if existing:
        raise DuplicatePublishError(
            f"Content #{content_id} was already published to LinkedIn (post "
            f"{existing.external_post_id}) at {existing.published_at}. Refusing to publish again.",
            existing_record=existing,
        )

    if not hitl_service.is_publishable(content.status, content.compliance_status):
        raise PublishingGateError(
            f"Cannot publish content #{content_id} to LinkedIn unless status='approved' AND "
            f"compliance_status='passed'. Current: status='{content.status}', "
            f"compliance_status='{content.compliance_status}'."
        )

    image_path, video_path = _extract_media(content)
    text = content.content_raw

    last_record: Optional[PublishingRecord] = None
    for attempt in range(1, max_attempts + 1):
        record = PublishingRecord(
            content_id=content_id,
            platform=PLATFORM,
            attempt=attempt,
            status="publishing",
            scheduled_at=datetime.now(timezone.utc),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        last_record = record

        try:
            if video_path:
                result = await linkedin_client.publish_video(text, Path(video_path))
            elif image_path:
                result = await linkedin_client.publish_image(text, Path(image_path))
            else:
                result = await linkedin_client.publish_text(text)

            record.status = "published"
            record.external_post_id = result["external_post_id"]
            record.published_at = datetime.now(timezone.utc)
            content.status = "published"
            db.commit()
            db.refresh(record)
            logger.info(
                f"[publishing] content #{content_id} published to LinkedIn as "
                f"{result['external_post_id']} (attempt {attempt})"
            )
            return record

        except (LinkedInNotConfiguredError, LinkedInPermanentError) as e:
            record.status = "failed"
            record.error_info = f"permanent: {e.message}"
            db.commit()
            logger.error(f"[publishing] content #{content_id} LinkedIn publish permanently failed: {e.message}")
            return record

        except LinkedInTransientError as e:
            record.status = "failed"
            record.error_info = f"transient (attempt {attempt}/{max_attempts}): {e.message}"
            db.commit()
            logger.warning(
                f"[publishing] content #{content_id} LinkedIn publish attempt {attempt} failed transiently: {e.message}"
            )
            if attempt < max_attempts:
                await asyncio.sleep(backoff_seconds * attempt)
            continue

    logger.error(f"[publishing] content #{content_id} exhausted {max_attempts} attempts, giving up")
    return last_record
