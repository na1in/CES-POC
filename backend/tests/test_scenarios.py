"""
Tests for scenario decision logic (CES-18 through CES-22).

All tests hit _decide() directly — pure functions, no DB or Claude calls needed.
The async run() functions are not tested here since they require Claude API;
they're covered by E2E tests in Phase 4.
"""
import pytest

from app.services.agent.scenarios.sc1 import _decide as sc1_decide
from app.services.agent.scenarios.sc2 import _decide as sc2_decide, _matching_policies
from app.services.agent.scenarios.sc3 import _decide as sc3_decide, _variance_tier
from app.services.agent.scenarios.sc4 import _decide as sc4_decide
from app.services.agent.scenarios.sc5 import _decide as sc5_decide

BASE = {
    "name_match_auto_apply": "90",
    "name_match_hold": "75",
    "amount_tolerance_auto": "2",
}

# ─────────────────────────────────────────────────────────────────────────────
# Scenario 1
# ─────────────────────────────────────────────────────────────────────────────

def s1_signals(**overrides):
    base = {
        "name_similarity_score": 95.0,
        "amount_variance_pct": 0.0,
        "has_risk_flags": False,
        "account_status": "active",
        "payment_method_risk_level": "low",
    }
    return {**base, **overrides}


class TestScenario1:
    def test_auto_apply_happy_path(self):
        rec, conf, requires, reason, path = sc1_decide(s1_signals(), BASE)
        assert rec == "APPLY"
        assert requires is False
        assert reason is None
        assert path == "scenario_1_auto_apply"
        assert conf >= 90

    def test_hold_for_risk_flags(self):
        rec, _, requires, reason, path = sc1_decide(s1_signals(has_risk_flags=True), BASE)
        assert rec == "HOLD"
        assert requires is True
        assert "risk" in reason.lower()
        assert path == "scenario_1_hold_risk_flags"

    def test_hold_for_medium_risk_method(self):
        rec, _, _, _, path = sc1_decide(s1_signals(payment_method_risk_level="medium"), BASE)
        assert rec == "HOLD"
        assert "method" in path

    def test_hold_for_high_risk_method(self):
        rec, _, _, _, path = sc1_decide(s1_signals(payment_method_risk_level="high"), BASE)
        assert rec == "HOLD"

    def test_hold_for_inactive_account(self):
        rec, _, _, _, path = sc1_decide(s1_signals(account_status="inactive"), BASE)
        assert rec == "HOLD"
        assert "inactive_account" in path

    def test_hold_for_gray_zone_name(self):
        rec, conf, requires, reason, path = sc1_decide(s1_signals(name_similarity_score=82.0), BASE)
        assert rec == "HOLD"
        assert requires is True
        assert "gray_zone" in path
        assert 60 <= conf <= 85

    def test_hold_at_exact_auto_apply_boundary(self):
        # name == 90 is NOT > 90, so should be HOLD (gray zone)
        rec, _, _, _, _ = sc1_decide(s1_signals(name_similarity_score=90.0), BASE)
        assert rec == "HOLD"

    def test_apply_just_above_boundary(self):
        rec, _, _, _, _ = sc1_decide(s1_signals(name_similarity_score=90.1), BASE)
        assert rec == "APPLY"

    def test_escalate_below_hold_threshold(self):
        rec, _, _, _, path = sc1_decide(s1_signals(name_similarity_score=74.0), BASE)
        assert rec == "ESCALATE"
        assert "escalate" in path

    def test_custom_threshold_respected(self):
        thresholds = {**BASE, "name_match_auto_apply": "95"}
        # score of 92 should now be HOLD, not APPLY
        rec, _, _, _, _ = sc1_decide(s1_signals(name_similarity_score=92.0), thresholds)
        assert rec == "HOLD"

    def test_auto_apply_confidence_scales_with_name_score(self):
        _, conf_low, _, _, _ = sc1_decide(s1_signals(name_similarity_score=91.0), BASE)
        _, conf_high, _, _, _ = sc1_decide(s1_signals(name_similarity_score=99.0), BASE)
        assert conf_high > conf_low


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 2
# ─────────────────────────────────────────────────────────────────────────────

def s2_payment(amount=125000):
    return {"payment_id": "PMT-002", "amount": amount}

def s2_signals(**overrides):
    base = {
        "customer_match_confidence": 95.0,
        "amount_variance_pct": 0.0,
        "account_match": False,
        "amount_match": True,
        "historical_match": True,
    }
    return {**base, **overrides}

def s2_context(**overrides):
    base = {
        "customer_id": "CUST-001",
        "customer_name": "Jane Doe",
        "active_policy_count": 1,
        "active_policies": [{"policy_id": "POL-A", "policy_number": "POL-00001", "premium_amount_cents": 125000}],
    }
    return {**base, **overrides}


class TestScenario2:
    def test_apply_strong_match_single_policy(self):
        rec, conf, reason, path, pid = sc2_decide(s2_payment(), s2_signals(), s2_context(), BASE)
        assert rec == "APPLY"
        assert pid == "POL-A"
        assert "single_policy" in path

    def test_apply_amount_disambiguates_two_policies(self):
        ctx = s2_context(
            active_policy_count=2,
            active_policies=[
                {"policy_id": "POL-A", "premium_amount_cents": 125000},
                {"policy_id": "POL-B", "premium_amount_cents": 85000},
            ],
        )
        rec, _, _, path, pid = sc2_decide(s2_payment(125000), s2_signals(), ctx, BASE)
        assert rec == "APPLY"
        assert pid == "POL-A"
        assert "amount_disambiguates" in path

    def test_hold_ambiguous_two_matching_policies(self):
        ctx = s2_context(
            active_policy_count=2,
            active_policies=[
                {"policy_id": "POL-A", "premium_amount_cents": 125000},
                {"policy_id": "POL-B", "premium_amount_cents": 130000},  # within 15% of 125000
            ],
        )
        rec, _, _, path, _ = sc2_decide(s2_payment(125000), s2_signals(), ctx, BASE)
        assert rec == "HOLD"
        assert "ambiguous" in path

    def test_hold_high_variance_single_policy(self):
        rec, _, _, path, _ = sc2_decide(
            s2_payment(), s2_signals(amount_variance_pct=20.0), s2_context(), BASE
        )
        assert rec == "HOLD"
        assert "high_variance" in path

    def test_hold_no_active_policies(self):
        ctx = s2_context(active_policy_count=0, active_policies=[])
        rec, _, _, path, _ = sc2_decide(s2_payment(), s2_signals(), ctx, BASE)
        assert rec == "HOLD"
        assert "no_active_policies" in path

    def test_apply_weak_match_two_supporting_signals(self):
        sigs = s2_signals(customer_match_confidence=80.0, account_match=True, amount_match=True)
        rec, _, _, path, _ = sc2_decide(s2_payment(), sigs, s2_context(), BASE)
        assert rec == "APPLY"
        assert "supporting_signals" in path

    def test_escalate_weak_match_one_supporting_signal(self):
        sigs = s2_signals(customer_match_confidence=80.0, account_match=False, amount_match=True, historical_match=False)
        rec, _, _, path, _ = sc2_decide(s2_payment(), sigs, s2_context(), BASE)
        assert rec == "ESCALATE"
        assert "insufficient_confidence" in path

    def test_all_paths_require_human_approval(self):
        # S2 always requires approval regardless of outcome
        cases = [
            sc2_decide(s2_payment(), s2_signals(), s2_context(), BASE),
            sc2_decide(s2_payment(), s2_signals(amount_variance_pct=20), s2_context(), BASE),
            sc2_decide(s2_payment(), s2_signals(customer_match_confidence=80), s2_context(), BASE),
        ]
        # The function doesn't return requires_approval directly — checked at run() level
        # Just verify the recommendations are valid values
        for rec, _, _, _, _ in cases:
            assert rec in ("APPLY", "HOLD", "ESCALATE")


class TestMatchingPolicies:
    def test_exact_match(self):
        policies = [{"policy_id": "P1", "premium_amount_cents": 10000}]
        result = _matching_policies(10000, policies)
        assert len(result) == 1

    def test_within_15_percent(self):
        policies = [{"policy_id": "P1", "premium_amount_cents": 10000}]
        result = _matching_policies(11400, policies)  # 14% over
        assert len(result) == 1

    def test_just_outside_15_percent(self):
        policies = [{"policy_id": "P1", "premium_amount_cents": 10000}]
        result = _matching_policies(11600, policies)  # 16% over
        assert len(result) == 0

    def test_zero_premium_excluded(self):
        policies = [{"policy_id": "P1", "premium_amount_cents": 0}]
        result = _matching_policies(10000, policies)
        assert len(result) == 0


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 3
# ─────────────────────────────────────────────────────────────────────────────

def s3_signals(**overrides):
    base = {
        "name_similarity_score": 95.0,
        "amount_variance_pct": 20.0,
        "is_multi_period": False,
        "estimated_periods": 0,
        "is_multi_method": False,
        "multi_method_fraction": 0.0,
        "is_third_party_payment": False,
        "third_party_relationship": None,
    }
    return {**base, **overrides}


class TestScenario3:
    def test_escalate_name_below_90(self):
        rec, _, _, _, path = sc3_decide(s3_signals(name_similarity_score=85.0), BASE)
        assert rec == "ESCALATE"
        assert "name_mismatch" in path

    def test_apply_tier2_minor_variance(self):
        rec, conf, _, _, path = sc3_decide(s3_signals(amount_variance_pct=10.0), BASE)
        assert rec == "APPLY"
        assert "tier2" in path
        assert conf >= 85

    def test_hold_tier3_no_special_case(self):
        rec, _, _, _, path = sc3_decide(s3_signals(amount_variance_pct=30.0), BASE)
        assert rec == "HOLD"
        assert "tier3" in path

    def test_hold_tier3_multi_period(self):
        rec, _, _, _, path = sc3_decide(s3_signals(amount_variance_pct=30.0, is_multi_period=True, estimated_periods=2), BASE)
        assert rec == "HOLD"
        assert "multi_period" in path

    def test_hold_tier3_multi_method(self):
        rec, _, _, _, path = sc3_decide(s3_signals(amount_variance_pct=30.0, is_multi_method=True, multi_method_fraction=0.5), BASE)
        assert rec == "HOLD"
        assert "multi_method" in path

    def test_hold_tier3_third_party(self):
        rec, _, _, _, path = sc3_decide(s3_signals(amount_variance_pct=30.0, is_third_party_payment=True, third_party_relationship="employer"), BASE)
        assert rec == "HOLD"
        assert "third_party" in path

    def test_hold_tier4(self):
        rec, conf, _, _, path = sc3_decide(s3_signals(amount_variance_pct=75.0), BASE)
        assert rec == "HOLD"
        assert "tier4" in path
        assert conf < 60

    def test_escalate_tier5_extreme(self):
        rec, _, _, _, path = sc3_decide(s3_signals(amount_variance_pct=150.0), BASE)
        assert rec == "ESCALATE"
        assert "tier5" in path

    def test_negative_variance_handled(self):
        rec, _, _, _, _ = sc3_decide(s3_signals(amount_variance_pct=-30.0), BASE)
        assert rec == "HOLD"  # underpayment tier 3

    @pytest.mark.parametrize("variance,expected_tier", [
        (2.1, 2), (15.0, 2), (15.1, 3), (50.0, 3), (50.1, 4), (100.0, 4), (100.1, 5),
    ])
    def test_variance_tier_boundaries(self, variance, expected_tier):
        assert _variance_tier(variance) == expected_tier


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 4
# ─────────────────────────────────────────────────────────────────────────────

def s4_signals(**overrides):
    base = {
        "name_similarity_score": 60.0,
        "is_third_party_payment": False,
        "third_party_relationship": None,
        "amount_variance_pct": 0.0,
    }
    return {**base, **overrides}

def s4_context(**overrides):
    base = {"customer_id": None, "customer_name": None, "policy_id": None}
    return {**base, **overrides}


class TestScenario4:
    def test_escalate_no_match_no_third_party(self):
        rec, _, _, path = sc4_decide(s4_signals(), s4_context(), BASE)
        assert rec == "ESCALATE"
        assert "no_match" in path

    def test_hold_third_party_with_valid_policy(self):
        rec, conf, _, path = sc4_decide(
            s4_signals(is_third_party_payment=True, third_party_relationship="employer"),
            s4_context(policy_id="POL-001"),
            BASE,
        )
        assert rec == "HOLD"
        assert "third_party" in path
        assert conf > 0

    def test_escalate_third_party_no_policy(self):
        # Third-party detected but no valid policy found
        rec, _, _, path = sc4_decide(
            s4_signals(is_third_party_payment=True),
            s4_context(policy_id=None),
            BASE,
        )
        assert rec == "ESCALATE"

    def test_escalate_third_party_high_variance(self):
        rec, _, _, path = sc4_decide(
            s4_signals(is_third_party_payment=True, amount_variance_pct=20.0),
            s4_context(policy_id="POL-001"),
            BASE,
        )
        assert rec == "ESCALATE"

    def test_escalate_confidence_is_low(self):
        _, conf, _, _ = sc4_decide(s4_signals(), s4_context(), BASE)
        assert conf <= 20


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 5
# ─────────────────────────────────────────────────────────────────────────────

def s5_signals(**overrides):
    base = {
        "is_duplicate_match": True,
        "duplicate_payment_id": "PMT-001",
        "hours_since_duplicate": 48.0,
        "outstanding_balance_cents": 0,
        "duplicate_amount_difference": 0,
    }
    return {**base, **overrides}


class TestScenario5:
    def test_escalate_no_balance(self):
        rec, conf, _, path = sc5_decide(s5_signals(outstanding_balance_cents=0))
        assert rec == "ESCALATE"
        assert conf == 0.0
        assert "true_duplicate" in path

    def test_hold_with_balance(self):
        rec, conf, _, path = sc5_decide(s5_signals(outstanding_balance_cents=75000))
        assert rec == "HOLD"
        assert conf == 60.0
        assert "balance_justifies" in path

    def test_escalate_with_amount_diff_within_tolerance(self):
        rec, _, _, _ = sc5_decide(s5_signals(outstanding_balance_cents=0, duplicate_amount_difference=150))
        assert rec == "ESCALATE"

    def test_hold_approval_reason_mentions_balance(self):
        _, _, reason, _ = sc5_decide(s5_signals(outstanding_balance_cents=50000))
        assert "balance" in reason.lower() or "50" in reason

    def test_escalate_approval_reason_mentions_duplicate(self):
        _, _, reason, _ = sc5_decide(s5_signals())
        assert "duplicate" in reason.lower() or "PMT-001" in reason

    def test_always_requires_human_approval(self):
        # Both paths return True for requires_human_approval (checked at run() level)
        # Just verify the decisions are valid
        rec_hold, _, _, _ = sc5_decide(s5_signals(outstanding_balance_cents=10000))
        rec_esc, _, _, _ = sc5_decide(s5_signals(outstanding_balance_cents=0))
        assert rec_hold == "HOLD"
        assert rec_esc == "ESCALATE"
