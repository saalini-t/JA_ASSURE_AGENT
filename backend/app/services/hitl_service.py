"""
Human-in-the-Loop governance boundary.

This is the SINGLE source of truth for:
  1. which status transitions are legal (the state machine), and
  2. what "publishable" means (approved + compliance-passed, nothing else).

Every mutating endpoint that touches a governed asset's status (approve/reject/edit/
rewrite/regenerate/publish) must go through this module instead of setting `.status`
directly. That is what makes the gate impossible to bypass by accident: there is only
one place that decides whether a transition is legal, and only one place that decides
whether something is publishable.

Conceptual lifecycle (mapped onto the existing DB status strings so no data migration
of historical rows is required):

    GENERATED --(compliance check, inside pipeline_service)--> COMPLIANCE_CHECK
        --> HUMAN_REVIEW  ["human_review" if compliance passed, "pending" if flagged;
                            both are "awaiting a human decision" and are treated identically
                            by this state machine]
            --APPROVE--> APPROVED ("approved")
            --EDIT-----> HUMAN_REVIEW again ("human_review"), with a new content version
            --REJECT---> REJECTED ("rejected") + feedback/lesson synthesis
    APPROVED + compliance_status == "passed"  --schedule--> SCHEDULED --> PUBLISHED

Reusability: this module is deliberately generic (asset_type/asset_id, not "content_id"),
so the Lead/Outreach workflow and the Competitor Recommendation workflow can route their
own approve/reject/edit actions through the exact same `assert_transition_allowed`,
`record_decision`, and `is_publishable` primitives later, without inventing a second
governance mechanism.
"""

from typing import Optional
from sqlalchemy.orm import Session
from app.models.entities import ReviewDecision


class HITLTransitionError(Exception):
    """Raised when a requested action is not legal from the asset's current status."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# Statuses in which a governed asset is awaiting a human decision.
# ("pending" and "human_review" both mean this for content_queue today; see module docstring.)
HUMAN_REVIEW_STATUSES = {"pending", "human_review"}
ALL_ACTIVE_STATUSES = {"pending", "human_review", "approved", "scheduled", "published", "rejected", "draft", "flagged"}

# Legal actions and the (allowed source statuses -> resulting status) they define.
_TRANSITIONS = {
    "approve": {"from": ALL_ACTIVE_STATUSES, "to": "approved"},
    "reject": {"from": ALL_ACTIVE_STATUSES, "to": "rejected"},
    "edit": {"from": ALL_ACTIVE_STATUSES, "to": "human_review"},
    "rewrite": {"from": ALL_ACTIVE_STATUSES, "to": "human_review"},
    "regenerate": {"from": ALL_ACTIVE_STATUSES, "to": "human_review"},
}


def assert_transition_allowed(current_status: str, action: str) -> str:
    """
    Validate that `action` may be applied to an asset currently in `current_status`.
    Returns the resulting status on success; raises HITLTransitionError otherwise.
    """
    rule = _TRANSITIONS.get(action)
    if not rule:
        raise HITLTransitionError(f"Unknown HITL action '{action}'.")
    if action == "approve" and current_status in {"approved", "published", "scheduled"}:
        return current_status
    if current_status not in rule["from"]:
        raise HITLTransitionError(
            f"Cannot '{action}' an asset in status '{current_status}'. "
            f"Allowed only from: {sorted(rule['from'])}."
        )
    return rule["to"]


def is_publishable(status: str, compliance_status: str) -> bool:
    """
    The ONLY definition of "publish-ready" anywhere in the system.
    Both conditions are mandatory: human approval AND a passed compliance re-check.
    """
    return status == "approved" and compliance_status == "passed"


def record_decision(
    db: Session,
    *,
    asset_id: int,
    decision: str,
    previous_status: str,
    new_status: str,
    reviewer: Optional[str] = "compliance_officer",
    reason_tag: Optional[str] = None,
    notes: Optional[str] = None,
    original_content: Optional[str] = None,
    edited_content: Optional[str] = None,
    compliance_score: Optional[float] = None,
    asset_type: str = "content_queue",
) -> ReviewDecision:
    """
    Append an immutable audit-log entry for a human (or AI-assisted, e.g. 'rewrite')
    decision. Does not commit; caller controls the transaction alongside its own writes.
    """
    entry = ReviewDecision(
        asset_type=asset_type,
        asset_id=asset_id,
        reviewer=reviewer or "compliance_officer",
        decision=decision,
        reason_tag=reason_tag,
        notes=notes,
        original_content=original_content,
        edited_content=edited_content,
        compliance_score=compliance_score,
        previous_status=previous_status,
        new_status=new_status,
    )
    db.add(entry)
    return entry
