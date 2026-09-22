"""
Competitor intelligence hardening: snapshot history and change-detection digests.

research_service.py's scrape/analyze/scoring logic is exercised through
_save_or_update_competitor directly (constructing a ResearchFinding by hand) rather
than mocking httpx + Groq end to end -- these tests are about the NEW snapshot/digest
behavior specifically, not re-testing the existing scraper (already covered by
test_ai_intelligence_layer.py).
"""
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal
from app.models.entities import Competitor, CompetitorSnapshot
from app.schemas.agent_contracts import ResearchFinding
from app.services.research_service import research_service

client = TestClient(app)


def _finding(**overrides) -> ResearchFinding:
    defaults = dict(
        source="https://example-competitor.test",
        source_type="VERIFIED_SOURCE",
        title="Example Competitor Homepage",
        company="Example Competitor Co",
        category="jewellery",
        market_country="Singapore",
        summary="Offers standard bridal jewellery insurance with a $5,000 cap.",
        offerings=["Bridal cover"],
        positioning="Budget-focused mass market positioning.",
        target_audience="Retail jewellery buyers",
        notable_claims=["Under $5,000 cap"],
        content_opportunities=["Highlight uncapped agreed-value coverage"],
        potential_weaknesses=[],
        counter_positioning="Observed messaging does not address high-value collections; whitespace for Jade.",
        confidence=0.9,
    )
    defaults.update(overrides)
    return ResearchFinding(**defaults)


def test_saving_a_new_competitor_creates_one_baseline_snapshot():
    url = "https://baseline-test-competitor.test"
    research_service._save_or_update_competitor("jade", url, _finding(source=url))

    db = SessionLocal()
    try:
        comp = db.query(Competitor).filter(Competitor.url == url).first()
        assert comp is not None
        snapshots = db.query(CompetitorSnapshot).filter(CompetitorSnapshot.competitor_id == comp.id).all()
        assert len(snapshots) == 1
    finally:
        db.close()


def test_repeated_saves_create_one_snapshot_per_run_not_overwritten():
    url = "https://repeated-save-test-competitor.test"
    research_service._save_or_update_competitor("jade", url, _finding(source=url, summary="First summary."))
    research_service._save_or_update_competitor("jade", url, _finding(source=url, summary="Second summary, changed."))

    db = SessionLocal()
    try:
        comp = db.query(Competitor).filter(Competitor.url == url).first()
        snapshots = db.query(CompetitorSnapshot).filter(CompetitorSnapshot.competitor_id == comp.id).order_by(CompetitorSnapshot.id).all()
        assert len(snapshots) == 2
        assert snapshots[0].summary == "First summary."
        assert snapshots[1].summary == "Second summary, changed."
        # the "latest state" cache reflects only the newest save
        assert comp.summary == "Second summary, changed."
    finally:
        db.close()


def test_digest_reports_baseline_when_only_one_snapshot_exists():
    url = "https://baseline-digest-test-competitor.test"
    research_service._save_or_update_competitor("jade", url, _finding(source=url))

    db = SessionLocal()
    comp_id = db.query(Competitor).filter(Competitor.url == url).first().id
    db.close()

    digest = research_service.get_competitor_digest(comp_id)
    assert digest.has_change is False
    assert digest.previous_state is None
    assert "baseline" in digest.note.lower()


def test_digest_detects_a_real_change_between_two_snapshots():
    url = "https://change-detected-test-competitor.test"
    research_service._save_or_update_competitor(
        "jade", url, _finding(source=url, summary="Offers a $5,000 cap on bridal jewellery.")
    )
    research_service._save_or_update_competitor(
        "jade", url, _finding(
            source=url, summary="Now offers a $15,000 cap and instant mobile appraisal.",
            counter_positioning="Observed messaging still lacks agreed-value coverage; whitespace for Jade.",
        )
    )

    db = SessionLocal()
    comp_id = db.query(Competitor).filter(Competitor.url == url).first().id
    db.close()

    digest = research_service.get_competitor_digest(comp_id)
    assert digest.has_change is True
    assert "summary" in digest.changed_fields
    assert digest.previous_state["summary"] == "Offers a $5,000 cap on bridal jewellery."
    assert digest.current_state["summary"] == "Now offers a $15,000 cap and instant mobile appraisal."
    assert digest.why_it_matters is not None
    assert digest.suggested_action is not None


def test_digest_reports_no_change_when_content_is_identical():
    url = "https://no-change-test-competitor.test"
    finding = _finding(source=url, summary="Stable offering, unchanged.")
    research_service._save_or_update_competitor("jade", url, finding)
    research_service._save_or_update_competitor("jade", url, finding)

    db = SessionLocal()
    comp_id = db.query(Competitor).filter(Competitor.url == url).first().id
    db.close()

    digest = research_service.get_competitor_digest(comp_id)
    assert digest.has_change is False
    assert digest.changed_fields == []
    assert digest.why_it_matters is None  # never claims significance for a non-change
    assert "no textual change" in digest.note.lower()


def test_digest_never_speculates_for_a_competitor_with_no_snapshot_at_all():
    # Created via the plain POST endpoint, never researched/analyzed -- no snapshot exists.
    res = client.post("/api/v1/competitors", json={
        "name": "Never Researched Co", "category": "jewellery",
        "title": "Placeholder", "summary": "Manually added, not yet researched.",
    })
    assert res.status_code == 201
    comp_id = res.json()["id"]

    digest = research_service.get_competitor_digest(comp_id)
    assert digest.has_change is False
    assert "no research snapshot exists" in digest.note.lower()


def test_digest_endpoint_404s_for_missing_competitor():
    res = client.get("/api/v1/competitors/999999/digest")
    assert res.status_code == 404


def test_snapshots_endpoint_returns_full_history_in_order():
    url = "https://snapshot-history-test-competitor.test"
    research_service._save_or_update_competitor("jade", url, _finding(source=url, summary="v1"))
    research_service._save_or_update_competitor("jade", url, _finding(source=url, summary="v2"))
    research_service._save_or_update_competitor("jade", url, _finding(source=url, summary="v3"))

    db = SessionLocal()
    comp_id = db.query(Competitor).filter(Competitor.url == url).first().id
    db.close()

    res = client.get(f"/api/v1/competitors/{comp_id}/snapshots")
    assert res.status_code == 200
    summaries = [s["summary"] for s in res.json()]
    assert summaries == ["v1", "v2", "v3"]


def test_all_digests_endpoint_returns_a_list():
    res = client.get("/api/v1/competitors/digest")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
