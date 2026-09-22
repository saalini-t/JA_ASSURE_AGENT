"""
Comprehensive Test Suite for Hardened Compliance Agent
Covers 20 rigorous test scenarios validating:
1.  Clean compliant content passes (score >= 85, status=PASS)
2.  Guaranteed payout blocked (RULE-01-GUARANTEED-OUTCOME, CRITICAL, status=BLOCKED)
3.  Guaranteed coverage blocked (RULE-01-GUARANTEED-OUTCOME, CRITICAL)
4.  Unsupported universal coverage claim blocked (RULE-02-UNIVERSAL-COVERAGE, CRITICAL)
5.  Medical advice/diagnosis blocked for DoctorShield (RULE-03-MEDICAL-ADVICE, CRITICAL)
6.  Pricing superlatives penalized (RULE-04-PRICING-SUPERLATIVE, MEDIUM)
7.  Unsupported competitor disparagement penalized (RULE-05-COMPETITOR-DISPARAGEMENT, HIGH)
8.  Missing disclaimer flagged (RULE-06-MISSING-DISCLAIMER, is_absence_rule=True)
9.  Unsupported statistics flagged (RULE-07-UNSUPPORTED-STATISTICS, MEDIUM)
10. Automatic payout promise blocked (RULE-08-AUTOMATIC-PAYOUT, CRITICAL)
11. Compound multiple violations compound penalties
12. Critical violation overrides high score (status remains BLOCKED regardless of score)
13. Deterministic vs LLM conflict resolution (deterministic engine overrides LLM false-pass)
14. Compliance rewrite fixes violations and appends disclaimer
15. Rewrite triggers mandatory independent recheck
16. Non-compliant rewrite remains blocked if violations persist
17. Human approval gate: unapproved/pending/flagged cannot reach publishing dispatch
18. Brand context sensitivity (Jade vs DoctorShield vs Jaguar Transit)
19. Jurisdiction context sensitivity (SG MAS vs MY BNM vs ID OJK vs TH OIC vs HK IA)
20. Platform and language context (X platform character constraints, multi-language context)
"""

import asyncio
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.compliance_service import compliance_service
from app.services.compliance.context import ComplianceContextResolver
from app.services.compliance.rules import ComplianceRuleRegistry
from app.schemas.agent_contracts import ComplianceResult

client = TestClient(app)


def test_01_clean_compliant_content_passes():
    """1. Clean compliant copy with proper disclaimers passes with high score and PASS status."""
    text = (
        "Jade provides bespoke jewellery and specie insurance solutions tailored for private collections "
        "and retail jewellers across Southeast Asia. Underwritten by licensed insurers. "
        "Terms and conditions apply. Subject to formal underwriting approval."
    )
    res = asyncio.run(
        compliance_service.evaluate_content(
            brand="jade",
            content_text=text,
            jurisdiction="SG",
            skip_llm=True,
        )
    )
    assert res.passed is True
    assert res.score >= 85
    assert res.status == "PASS"
    assert len(res.violations) == 0
    assert res.disclaimer_status in ["compliant", "PRESENT", "SATISFIED"]


def test_02_guaranteed_payout_blocked():
    """2. Guaranteed payout promise is blocked with CRITICAL severity under RULE-01."""
    text = "Jade promises a 100% guaranteed payout within 24 hours for any stolen gemstones."
    res = asyncio.run(
        compliance_service.evaluate_content(
            brand="jade",
            content_text=text,
            skip_llm=True,
        )
    )
    assert res.passed is False
    assert res.status == "BLOCKED"
    rule_01 = next((v for v in res.violations if v.rule_id == "RULE-01-GUARANTEED-OUTCOME"), None)
    assert rule_01 is not None
    assert rule_01.severity == "CRITICAL"
    assert rule_01.matched_text is not None
    assert len(rule_01.matched_text) > 0


def test_03_guaranteed_coverage_blocked():
    """3. Guaranteed coverage for all claims is blocked under RULE-01."""
    text = "We provide guaranteed coverage for every physician regardless of malpractice history."
    res = asyncio.run(
        compliance_service.evaluate_content(
            brand="doctorshield",
            content_text=text,
            skip_llm=True,
        )
    )
    assert res.passed is False
    assert res.status == "BLOCKED"
    assert any(v.rule_id == "RULE-01-GUARANTEED-OUTCOME" for v in res.violations)


def test_04_unsupported_universal_coverage_claim_blocked():
    """4. Claims of zero exclusions or universal coverage trigger RULE-02 with CRITICAL severity."""
    text = "Our policy offers zero exclusions and universal coverage for any cargo damage during transit."
    res = asyncio.run(
        compliance_service.evaluate_content(
            brand="jaguartransit",
            content_text=text,
            skip_llm=True,
        )
    )
    assert res.passed is False
    assert res.status == "BLOCKED"
    rule_02 = next((v for v in res.violations if "COVERAGE" in v.rule_id), None)
    assert rule_02 is not None
    assert rule_02.severity == "CRITICAL"


def test_05_medical_advice_diagnosis_blocked_for_doctorshield():
    """5. DoctorShield content offering clinical diagnosis or medical treatment is blocked under RULE-07."""
    text = "DoctorShield diagnoses clinical errors and prescribes medical negligence recovery protocols."
    res = asyncio.run(
        compliance_service.evaluate_content(
            brand="doctorshield",
            content_text=text,
            skip_llm=True,
        )
    )
    assert res.passed is False
    assert res.status == "BLOCKED"
    rule_03 = next((v for v in res.violations if "MEDICAL" in v.rule_id), None)
    assert rule_03 is not None
    assert rule_03.severity == "CRITICAL"


def test_06_pricing_superlatives_penalized():
    """6. Pricing superlatives (cheapest, lowest rates) trigger pricing rule with MEDIUM penalty."""
    text = (
        "Jade is the cheapest jewellery insurance in Singapore with the absolute lowest rates anywhere. "
        "Terms and conditions apply. Subject to underwriting approval."
    )
    res = asyncio.run(
        compliance_service.evaluate_content(
            brand="jade",
            content_text=text,
            skip_llm=True,
        )
    )
    all_issues = res.violations + res.warnings
    rule_04 = next((v for v in all_issues if "PRICING" in v.rule_id), None)
    assert rule_04 is not None
    assert rule_04.severity == "MEDIUM"
    assert res.score <= 85  # Deduction applied


def test_07_unsupported_competitor_disparagement_penalized():
    """7. Disparaging competitor insurers triggers competitor disparagement rule with HIGH severity penalty."""
    text = (
        "Competitor insurance providers are fraudulent scam companies that deny every claim. "
        "Terms and conditions apply. Subject to formal approval."
    )
    res = asyncio.run(
        compliance_service.evaluate_content(
            brand="jade",
            content_text=text,
            skip_llm=True,
        )
    )
    all_issues = res.violations + res.warnings
    rule_05 = next((v for v in all_issues if "COMPETITOR" in v.rule_id), None)
    assert rule_05 is not None
    assert rule_05.severity == "HIGH"
    assert res.score <= 75


def test_08_missing_disclaimer_flagged():
    """8. Absence of required regulatory disclaimer triggers absence rule RULE-06."""
    text = "Protect your gold and diamond inventory against theft during transit across Southeast Asia."
    res = asyncio.run(
        compliance_service.evaluate_content(
            brand="jade",
            content_text=text,
            skip_llm=True,
        )
    )
    all_issues = res.violations + res.warnings
    rule_06 = next((v for v in all_issues if "DISCLAIMER" in v.rule_id), None)
    assert rule_06 is not None
    assert res.disclaimer_status in ["missing", "MISSING"]


def test_09_unsupported_statistics_flagged():
    """9. Unsupported quantitative statistics trigger unsourced statistics rule."""
    text = (
        "99.9% of our jeweller clients save $50,000 every single year on insurance premiums. "
        "Terms and conditions apply."
    )
    res = asyncio.run(
        compliance_service.evaluate_content(
            brand="jade",
            content_text=text,
            skip_llm=True,
        )
    )
    all_issues = res.violations + res.warnings
    rule_07 = next((v for v in all_issues if "STATISTICS" in v.rule_id), None)
    assert rule_07 is not None
    assert rule_07.severity == "MEDIUM"


def test_10_automatic_payout_promise_blocked():
    """10. Automatic instantaneous payout promises trigger automatic payout rule with CRITICAL severity."""
    text = "Instant automatic approval with no questions asked for all damaged cargo. Terms apply."
    res = asyncio.run(
        compliance_service.evaluate_content(
            brand="jaguartransit",
            content_text=text,
            skip_llm=True,
        )
    )
    assert res.passed is False
    assert res.status == "BLOCKED"
    rule_08 = next((v for v in res.violations if "AUTOMATIC" in v.rule_id or "FALSE-CERTAINTY" in v.rule_id), None)
    assert rule_08 is not None
    assert rule_08.severity in ["CRITICAL", "HIGH"]


def test_11_compound_multiple_violations_compound_penalties():
    """11. Multiple compound violations compound numerical penalties and enforce BLOCKED status."""
    text = (
        "The cheapest insurance in Asia guarantees 100% payout with zero exclusions and instantaneous automatic approval."
    )
    res = asyncio.run(
        compliance_service.evaluate_content(
            brand="jade",
            content_text=text,
            skip_llm=True,
        )
    )
    assert res.passed is False
    assert res.status == "BLOCKED"
    # Triggers RULE-01 (Critical -35), RULE-02 (Critical -35), RULE-04 (Medium -15), RULE-08 (Critical -35)
    assert len(res.violations) >= 3
    assert res.score <= 30.0


def test_12_critical_violation_overrides_high_score():
    """12. A critical violation strictly forces status BLOCKED and passed=False regardless of score."""
    text = (
        "Our specialized policy includes a guaranteed payout for any gemstone defect. "
        "Underwritten by licensed insurers under MAS regulatory oversight. Terms and conditions apply."
    )
    res = asyncio.run(
        compliance_service.evaluate_content(
            brand="jade",
            content_text=text,
            skip_llm=True,
        )
    )
    # Even if mathematical deduction leaves 65 (100 - 35), status MUST be BLOCKED
    assert res.passed is False
    assert res.status == "BLOCKED"
    assert any(v.severity == "CRITICAL" for v in res.violations)


def test_13_deterministic_vs_llm_conflict_resolution():
    """13. Deterministic rule strictly overrides Groq LLM if LLM erroneously returns passed=True."""
    text = "We promise 100% guaranteed payout for any stolen luxury watch."
    
    mock_llm_eval = ComplianceResult(
        passed=True,
        score=98.0,
        status="PASS",
        violations=[],
        warnings=[],
        suggestions=[],
        overall_feedback="Looks completely fine!",
        disclaimers_required=[]
    )
    
    with patch("app.services.compliance.engine.llm_provider.generate_structured", return_value=mock_llm_eval):
        res = asyncio.run(
            compliance_service.evaluate_content(
                brand="jade",
                content_text=text,
                skip_llm=False,
            )
        )
        # Deterministic precedence check: deterministic RULE-01 MUST override LLM passed=True
        assert res.passed is False
        assert res.status == "BLOCKED"
        assert any(v.rule_id == "RULE-01-GUARANTEED-OUTCOME" for v in res.violations)


def test_14_compliance_rewrite_fixes_violations_and_appends_disclaimer():
    """14. Compliance rewrite sanitizes non-compliant language, appends disclaimers, and raises score."""
    original = "Jade offers 100% guaranteed payout with zero exclusions for all jewellers."
    rewrite_res = asyncio.run(
        compliance_service.rewrite_non_compliant_content(
            brand="jade",
            original_text=original,
            jurisdiction="SG",
            skip_llm=True,
        )
    )
    assert rewrite_res["previous_passed"] is False
    assert rewrite_res["previous_status"] == "BLOCKED"
    assert rewrite_res["new_score"] > rewrite_res["previous_score"]
    
    corrected = rewrite_res["corrected_text"].lower()
    assert "guaranteed payout" not in corrected
    assert "zero exclusions" not in corrected
    assert ("terms" in corrected or "underwritten" in corrected or "subject to" in corrected)


def test_15_rewrite_triggers_mandatory_independent_recheck():
    """15. Rewrite workflow must perform an independent recheck on the generated copy."""
    original = "Zero exclusions, universal coverage for every transit hazard."
    rewrite_res = asyncio.run(
        compliance_service.rewrite_non_compliant_content(
            brand="jaguartransit",
            original_text=original,
            jurisdiction="SG",
            skip_llm=True,
        )
    )
    assert "recheck_passed" in rewrite_res
    assert isinstance(rewrite_res["recheck_passed"], bool)
    assert "remediation_actions" in rewrite_res
    assert len(rewrite_res["remediation_actions"]) > 0
    assert "new_violations" in rewrite_res


def test_16_non_compliant_rewrite_remains_blocked_if_violations_persist():
    """16. If a rewrite fails to eliminate violations, recheck ensures status remains BLOCKED."""
    original = "Guaranteed payout for any gemstone."
    
    # Simulate an LLM that returns a rewrite that STILL contains a prohibited claim
    def bad_rewrite(*args, **kwargs):
        return "We still promise a 100% guaranteed payout for any gemstone loss."
        
    with patch.object(compliance_service.rewriter, "_generate_llm_rewrite", side_effect=bad_rewrite):
        rewrite_res = asyncio.run(
            compliance_service.rewrite_non_compliant_content(
                brand="jade",
                original_text=original,
                jurisdiction="SG",
                skip_llm=False,
            )
        )
        assert rewrite_res["new_passed"] is False
        assert rewrite_res["new_status"] == "BLOCKED"
        assert rewrite_res["recheck_passed"] is False


def test_17_human_approval_gate_unapproved_cannot_publish():
    """17. Content items in pending or human_review status cannot be scheduled or published."""
    # Find or verify a pending item in queue
    queue_res = client.get("/api/v1/queue")
    assert queue_res.status_code == 200
    items = queue_res.json()
    pending_item = next((i for i in items if i["status"] in ["pending", "human_review"]), None)
    
    if not pending_item:
        # Create a pending item to test
        create_res = client.post("/api/v1/queue", json={
            "brand": "jade",
            "platform": "linkedin",
            "topic": "Jewellery Governance Test",
            "content_raw": "Draft content awaiting review.",
            "status": "human_review",
            "compliance_status": "flagged",
            "compliance_score": 65.0
        })
        pending_item = create_res.json()

    # Attempt to schedule without human approval must return 400
    pub_res = client.post("/api/v1/publishing", json={
        "content_id": pending_item["id"],
        "platform": "linkedin"
    })
    assert pub_res.status_code == 400
    assert "Only human-approved content can reach publishing dispatch" in pub_res.json()["detail"]


def test_18_brand_context_sensitivity():
    """18. Context resolver sets distinct products and brand metadata for Jade, DoctorShield, and Jaguar Transit."""
    resolver = ComplianceContextResolver()
    
    ctx_jade = resolver.resolve("jade")
    assert ctx_jade.brand == "jade"
    assert "jewellery" in ctx_jade.product.lower()
    assert "jade" in ctx_jade.brand_display.lower()

    ctx_doc = resolver.resolve("doctorshield")
    assert ctx_doc.brand == "doctorshield"
    assert "medical" in ctx_doc.product.lower()
    assert "doctorshield" in ctx_doc.brand_display.lower()

    ctx_jag = resolver.resolve("jaguartransit")
    assert ctx_jag.brand == "jaguartransit"
    assert ("cargo" in ctx_jag.product.lower() or "transit" in ctx_jag.product.lower())
    assert "transit" in ctx_jag.brand_display.lower()


def test_19_jurisdiction_context_sensitivity():
    """19. Context resolver maps regulatory authorities across SG (MAS), MY (BNM), ID (OJK), TH (OIC), HK (IA)."""
    resolver = ComplianceContextResolver()
    
    ctx_sg = resolver.resolve("jade", jurisdiction="SG")
    assert "MAS" in ctx_sg.authority
    assert "MAS" in ctx_sg.default_disclaimer

    ctx_my = resolver.resolve("jade", jurisdiction="MY")
    assert "BNM" in ctx_my.authority
    assert "Bank Negara Malaysia" in ctx_my.default_disclaimer or "BNM" in ctx_my.default_disclaimer

    ctx_id = resolver.resolve("jade", jurisdiction="ID")
    assert "OJK" in ctx_id.authority
    assert "OJK" in ctx_id.default_disclaimer

    ctx_th = resolver.resolve("jade", jurisdiction="TH")
    assert "OIC" in ctx_th.authority
    assert "OIC" in ctx_th.default_disclaimer

    ctx_hk = resolver.resolve("jade", jurisdiction="HK")
    assert "IA" in ctx_hk.authority
    assert "IA" in ctx_hk.default_disclaimer


def test_20_platform_and_language_context():
    """20. Platform character limits and multi-language context are respected without errors."""
    # Platform X character constraint (> 280 chars)
    long_tweet = "A" * 320 + " Underwritten by licensed underwriters. Terms apply."
    res_x = asyncio.run(
        compliance_service.evaluate_content(
            brand="jade",
            content_text=long_tweet,
            platform="x",
            skip_llm=True,
        )
    )
    all_issues = res_x.violations + res_x.warnings
    assert any(v.rule_id == "RULE-11-PLATFORM-CONSTRAINT" for v in all_issues)

    # Multi-language evaluation (Malay and Chinese)
    res_ms = asyncio.run(
        compliance_service.evaluate_content(
            brand="jade",
            content_text="Perlindungan komprehensif untuk barang kemas berharga tinggi di Malaysia. Tertakluk kepada terma dan syarat.",
            language="ms",
            jurisdiction="MY",
            skip_llm=True,
        )
    )
    assert res_ms.jurisdiction in ["Malaysia", "MY"]
    assert res_ms.language == "ms"

    res_zh = asyncio.run(
        compliance_service.evaluate_content(
            brand="jade",
            content_text="专为高端珠宝和贵金属业务打造的专业保险方案。受条款和条件约束。",
            language="zh",
            jurisdiction="SG",
            skip_llm=True,
        )
    )
    assert res_zh.language == "zh"
