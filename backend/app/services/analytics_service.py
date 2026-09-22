from collections import Counter
from typing import Dict, Any
from sqlalchemy import select, func
from app.models.entities import ContentQueue, Lead, LessonLearned, Feedback
from app.database.session import SessionLocal
from app.schemas.dtos import DashboardSummary

class AnalyticsService:
    """
    Real-time KPI aggregation and closed-loop learning metrics engine.
    """

    def get_summary(self) -> DashboardSummary:
        db = SessionLocal()
        try:
            # 1. Content Queue Items
            items = db.execute(select(ContentQueue)).scalars().all()
            total_content = len(items)

            pending_compliance = sum(1 for i in items if i.compliance_status == "pending")
            pending_human_review = sum(1 for i in items if i.status == "human_review")
            compliance_approved = sum(1 for i in items if i.compliance_status == "passed")
            human_approved = sum(1 for i in items if i.status in ["approved", "published"])
            rejected = sum(1 for i in items if i.status == "rejected")
            published = sum(1 for i in items if i.status == "published")

            # Approval and Rejection rates
            evaluated_total = human_approved + rejected
            approval_rate = round((human_approved / evaluated_total * 100.0), 1) if evaluated_total > 0 else 0.0
            rejection_rate = round((rejected / evaluated_total * 100.0), 1) if evaluated_total > 0 else 0.0

            # Compliance scores & distribution
            compliance_scores = [i.compliance_score for i in items if i.compliance_score > 0]
            avg_compliance = round(sum(compliance_scores) / len(compliance_scores), 1) if compliance_scores else 0.0
            
            compliance_score_distribution = {
                "high_90_100": sum(1 for i in items if i.compliance_score >= 90.0),
                "medium_80_89": sum(1 for i in items if 80.0 <= i.compliance_score < 90.0),
                "flagged_below_80": sum(1 for i in items if 0.0 < i.compliance_score < 80.0),
                "90_100": sum(1 for i in items if i.compliance_score >= 90.0),
                "80_89": sum(1 for i in items if 80.0 <= i.compliance_score < 90.0),
                "<80": sum(1 for i in items if 0.0 < i.compliance_score < 80.0),
            }

            # Distributions
            brand_counts = dict(Counter(i.brand for i in items))
            platform_counts = dict(Counter(i.platform for i in items))
            language_counts = dict(Counter(i.language for i in items))
            status_counts = dict(Counter(i.status for i in items))

            # 2. Leads metrics & distribution
            leads = db.execute(select(Lead)).scalars().all()
            total_leads = len(leads)
            lead_scores = [l.fit_score for l in leads if l.fit_score > 0]
            avg_lead_score = round(sum(lead_scores) / len(lead_scores), 1) if lead_scores else 0.0

            lead_score_distribution = {
                "high_fit_80_plus": sum(1 for l in leads if l.fit_score >= 80.0),
                "moderate_fit_60_79": sum(1 for l in leads if 60.0 <= l.fit_score < 80.0),
                "general_below_60": sum(1 for l in leads if 0.0 < l.fit_score < 60.0),
                "tier_1_high": sum(1 for l in leads if l.fit_score >= 80.0),
                "tier_2_moderate": sum(1 for l in leads if 60.0 <= l.fit_score < 80.0),
                "tier_3_emerging": sum(1 for l in leads if 0.0 < l.fit_score < 60.0),
            }

            # 3. Lessons & Feedback
            total_lessons = db.execute(select(func.count(LessonLearned.id))).scalar() or 0
            active_lessons_count = db.execute(select(func.count(LessonLearned.id)).where(LessonLearned.active == True)).scalar() or 0
            
            feedbacks = db.execute(select(Feedback)).scalars().all()
            total_feedback_count = len(feedbacks)
            feedback_reasons = dict(Counter(f.reason_tag for f in feedbacks))

            # Edits and regenerations
            edited = sum(1 for i in items if i.reason_tag == "human_edit" or (i.notes and "Edited" in i.notes))
            regeneration_count = sum(1 for i in items if i.notes and "Regenerated" in i.notes)

            return DashboardSummary(
                total_content=total_content,
                pending_compliance=pending_compliance,
                pending_human_review=pending_human_review,
                compliance_approved=compliance_approved,
                human_approved=human_approved,
                approved=human_approved,
                rejected=rejected,
                edited=edited,
                published=published,
                approval_rate=approval_rate,
                rejection_rate=rejection_rate,
                average_compliance_score=avg_compliance,
                total_leads=total_leads,
                average_lead_score=avg_lead_score,
                total_lessons_learned=total_lessons,
                active_lessons_count=active_lessons_count,
                total_feedback_count=total_feedback_count,
                regeneration_count=regeneration_count,
                brand_breakdown=brand_counts,
                platform_breakdown=platform_counts,
                language_breakdown=language_counts,
                feedback_reason_frequency=feedback_reasons,
                compliance_score_distribution=compliance_score_distribution,
                lead_score_distribution=lead_score_distribution,
                status_breakdown=status_counts
            )
        finally:
            db.close()

analytics_service = AnalyticsService()
