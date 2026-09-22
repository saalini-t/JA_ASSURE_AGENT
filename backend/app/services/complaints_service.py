"""
Complaints Handling Service (Abhi Ram's contribution).
Handles capturing user/customer complaints, SQLite persistence, automated & manual
department routing, and the resolution lifecycle (pending -> under_review -> routed -> actioned -> resolved/rejected).
Operates strictly separated from the marketing content pipeline.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.entities import Complaint
from app.schemas.dtos import (
    ComplaintCreate,
    ComplaintUpdate,
    ComplaintRouteRequest,
    ComplaintActionRequest,
    ComplaintStatusUpdate,
    ComplaintMetricsResponse,
)

logger = logging.getLogger("ja_assure.complaints")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# Routing rules matrix
ROUTING_DEPARTMENT_MAP = {
    "claims_denial": "claims_desk",
    "policy_coverage": "underwriting_team",
    "compliance_misleading": "compliance_legal",
    "billing_dispute": "billing_support",
    "technical_issue": "technical_support",
    "customer_service": "customer_relations",
    "other": "customer_relations",
}


class ComplaintsService:
    """
    Complaints engine managing the lifecycle of customer complaints:
    1. Capture and SQLite persistence with unique tracking IDs.
    2. Intelligent automated triage & department routing based on complaint keywords and category.
    3. Manual routing and re-assignment for review/response.
    4. Actioning and resolution with full audit tracking.
    """

    def generate_complaint_number(self) -> str:
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        random_suffix = uuid.uuid4().hex[:6].upper()
        return f"CMP-{date_str}-{random_suffix}"

    def auto_classify_routing(self, complaint_in: ComplaintCreate) -> tuple[str, str, str]:
        """
        Determines recommended (priority, routed_to, routing_reason)
        based on subject, description, and category.
        """
        content = f"{complaint_in.subject} {complaint_in.description}".lower()
        priority = complaint_in.priority or "medium"

        # Check for urgent / regulatory escalation triggers
        urgent_keywords = ["lawsuit", "regulator", "mas", "police", "legal action", "court", "fraud", "monetary authority"]
        if any(kw in content for kw in urgent_keywords):
            return "urgent", "executive_escalations", "Auto-escalated: urgent regulatory or legal risk keywords detected"

        # Map by category
        category = complaint_in.category.lower() if complaint_in.category else "other"
        target_dept = ROUTING_DEPARTMENT_MAP.get(category, "customer_relations")

        if category == "claims_denial":
            reason = "Auto-routed: claims denial or payout dispute"
        elif category == "compliance_misleading":
            reason = "Auto-routed: potential marketing disclosure or MAS/MOH compliance concern"
        elif category == "policy_coverage":
            reason = "Auto-routed: policy wording, underwriting or coverage inquiry"
        elif category == "billing_dispute":
            reason = "Auto-routed: billing discrepancy or payment issue"
        elif category == "technical_issue":
            reason = "Auto-routed: portal or technical service disruption"
        else:
            reason = "Auto-routed: general customer inquiries"

        return priority, target_dept, reason

    def submit_complaint(self, db: Session, complaint_in: ComplaintCreate) -> Complaint:
        """
        Capture user/customer complaint, persist into SQLite, and auto-route.
        """
        complaint_number = self.generate_complaint_number()
        computed_priority, auto_dept, auto_reason = self.auto_classify_routing(complaint_in)

        # Allow user-specified priority if higher, otherwise use computed
        final_priority = complaint_in.priority if complaint_in.priority == "urgent" else computed_priority

        now = utc_now()
        complaint = Complaint(
            complaint_number=complaint_number,
            customer_name=complaint_in.customer_name.strip(),
            customer_email=complaint_in.customer_email.strip().lower(),
            customer_phone=complaint_in.customer_phone.strip() if complaint_in.customer_phone else None,
            brand=complaint_in.brand.strip().lower(),
            category=complaint_in.category.strip().lower(),
            priority=final_priority,
            subject=complaint_in.subject.strip(),
            description=complaint_in.description.strip(),
            status="pending",
            routed_to=auto_dept,
            routing_reason=auto_reason,
            routed_at=now,
            created_at=now,
            updated_at=now,
        )

        db.add(complaint)
        db.commit()
        db.refresh(complaint)

        logger.info(
            f"Created complaint {complaint.complaint_number} for brand '{complaint.brand}' "
            f"auto-routed to '{complaint.routed_to}' with priority '{complaint.priority}'."
        )
        return complaint

    def route_complaint(self, db: Session, complaint_id: int, route_req: ComplaintRouteRequest) -> Optional[Complaint]:
        """
        Route complaint to specific department and assigned reviewer.
        Transitions status from pending -> routed (or under_review if reviewer assigned).
        """
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not complaint:
            return None

        complaint.routed_to = route_req.routed_to
        if route_req.routing_reason:
            complaint.routing_reason = route_req.routing_reason
        if route_req.assigned_reviewer:
            complaint.assigned_reviewer = route_req.assigned_reviewer
            complaint.status = "under_review"
        else:
            complaint.status = "routed"

        complaint.routed_at = utc_now()
        complaint.updated_at = utc_now()

        db.commit()
        db.refresh(complaint)
        logger.info(f"Routed complaint #{complaint.id} ({complaint.complaint_number}) to {complaint.routed_to}")
        return complaint

    def action_complaint(self, db: Session, complaint_id: int, action_req: ComplaintActionRequest) -> Optional[Complaint]:
        """
        Action/resolve complaint: records resolution notes, response draft, actioned_by,
        and transitions status: actioned, resolved, or rejected.
        """
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not complaint:
            return None

        now = utc_now()
        action_type = action_req.action.lower()

        if action_type == "resolve":
            complaint.status = "resolved"
            complaint.resolved_at = now
        elif action_type == "reject":
            complaint.status = "rejected"
        elif action_type == "under_review":
            complaint.status = "under_review"
        else:
            complaint.status = "actioned"

        complaint.resolution_notes = action_req.resolution_notes
        if action_req.response_draft:
            complaint.response_draft = action_req.response_draft
        if action_req.actioned_by:
            complaint.actioned_by = action_req.actioned_by

        complaint.actioned_at = now
        complaint.updated_at = now

        db.commit()
        db.refresh(complaint)
        logger.info(f"Actioned complaint #{complaint.id}: status={complaint.status}, by={complaint.actioned_by}")
        return complaint

    def update_status(self, db: Session, complaint_id: int, status_update: ComplaintStatusUpdate) -> Optional[Complaint]:
        """
        Direct status transition following pending -> approved spirit:
        pending -> under_review -> routed -> actioned -> resolved / rejected.
        """
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not complaint:
            return None

        complaint.status = status_update.status
        if status_update.notes:
            existing = complaint.resolution_notes or ""
            complaint.resolution_notes = f"{existing}\n[Status Change Note]: {status_update.notes}".strip()

        if status_update.status == "resolved":
            complaint.resolved_at = utc_now()

        complaint.updated_at = utc_now()
        db.commit()
        db.refresh(complaint)
        return complaint

    def get_complaint_by_id(self, db: Session, complaint_id: int) -> Optional[Complaint]:
        return db.query(Complaint).filter(Complaint.id == complaint_id).first()

    def get_complaints(
        self,
        db: Session,
        brand: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        routed_to: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Complaint]:
        """Query complaints with flexible filters."""
        query = db.query(Complaint)

        if brand:
            query = query.filter(Complaint.brand == brand.lower())
        if status:
            query = query.filter(Complaint.status == status.lower())
        if priority:
            query = query.filter(Complaint.priority == priority.lower())
        if category:
            query = query.filter(Complaint.category == category.lower())
        if routed_to:
            query = query.filter(Complaint.routed_to == routed_to.lower())

        return query.order_by(Complaint.created_at.desc()).offset(offset).limit(limit).all()

    def get_metrics(self, db: Session) -> ComplaintMetricsResponse:
        """Aggregate summary statistics across all complaints in SQLite."""
        total = db.query(func.count(Complaint.id)).scalar() or 0
        pending = db.query(func.count(Complaint.id)).filter(Complaint.status == "pending").scalar() or 0
        routed = db.query(func.count(Complaint.id)).filter(Complaint.status == "routed").scalar() or 0
        actioned = db.query(func.count(Complaint.id)).filter(Complaint.status == "actioned").scalar() or 0
        resolved = db.query(func.count(Complaint.id)).filter(Complaint.status == "resolved").scalar() or 0
        rejected = db.query(func.count(Complaint.id)).filter(Complaint.status == "rejected").scalar() or 0

        # Brand breakdown
        brand_rows = db.query(Complaint.brand, func.count(Complaint.id)).group_by(Complaint.brand).all()
        brand_map = {b or "unknown": count for b, count in brand_rows}

        # Category breakdown
        cat_rows = db.query(Complaint.category, func.count(Complaint.id)).group_by(Complaint.category).all()
        cat_map = {c or "other": count for c, count in cat_rows}

        # Priority breakdown
        prio_rows = db.query(Complaint.priority, func.count(Complaint.id)).group_by(Complaint.priority).all()
        prio_map = {p or "medium": count for p, count in prio_rows}

        # Department breakdown
        dept_rows = db.query(Complaint.routed_to, func.count(Complaint.id)).group_by(Complaint.routed_to).all()
        dept_map = {d or "unassigned": count for d, count in dept_rows}

        return ComplaintMetricsResponse(
            total_complaints=total,
            pending_count=pending,
            routed_count=routed,
            actioned_count=actioned,
            resolved_count=resolved,
            rejected_count=rejected,
            brand_breakdown=brand_map,
            category_breakdown=cat_map,
            priority_breakdown=prio_map,
            department_breakdown=dept_map,
        )


complaints_service = ComplaintsService()
