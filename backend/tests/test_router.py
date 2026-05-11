"""
Tests for the deterministic scenario router (CES-17).

Unit tests cover _route() directly — no DB needed.
One integration test covers route_scenario() with real threshold loading.
"""
import pytest
from sqlalchemy import text

from app.services.agent.router import _route, _variance_tier, route_scenario

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BASE_THRESHOLDS = {
    "name_match_hold": "75",
    "amount_tolerance_auto": "2",
}


def signals(
    *,
    is_duplicate_match: bool = False,
    name_similarity_score: float = 95.0,
    amount_variance_pct: float = 0.0,
) -> dict:
    return {
        "is_duplicate_match": is_duplicate_match,
        "name_similarity_score": name_similarity_score,
        "amount_variance_pct": amount_variance_pct,
    }


def payment(*, extracted_policy_number: str | None = "POL-12345") -> dict:
    return {"payment_id": "PMT-001", "extracted_policy_number": extracted_policy_number}


# ---------------------------------------------------------------------------
# _variance_tier
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("pct,expected_tier", [
    (0.0, 1),
    (2.0, 1),
    (2.1, 2),
    (15.0, 2),
    (15.1, 3),
    (50.0, 3),
    (50.1, 4),
    (100.0, 4),
    (100.1, 5),
    (500.0, 5),
])
def test_variance_tier(pct, expected_tier):
    assert _variance_tier(pct) == expected_tier


# ---------------------------------------------------------------------------
# Scenario 5 — duplicate detection (highest priority)
# ---------------------------------------------------------------------------

def test_scenario_5_duplicate_takes_priority():
    result = _route(
        signals(is_duplicate_match=True, name_similarity_score=20.0, amount_variance_pct=200.0),
        payment(extracted_policy_number=None),
        BASE_THRESHOLDS,
    )
    assert result == (5, "scenario_5_duplicate")


def test_scenario_5_with_good_name_and_policy():
    """Duplicate flag overrides even a perfect scenario 1 match."""
    result = _route(
        signals(is_duplicate_match=True, name_similarity_score=100.0, amount_variance_pct=0.0),
        payment(extracted_policy_number="POL-99"),
        BASE_THRESHOLDS,
    )
    assert result[0] == 5


# ---------------------------------------------------------------------------
# Scenario 4 — no matching customer
# ---------------------------------------------------------------------------

def test_scenario_4_low_name_score():
    result = _route(signals(name_similarity_score=60.0), payment(), BASE_THRESHOLDS)
    assert result == (4, "scenario_4_no_customer_match")


def test_scenario_4_exactly_at_boundary_is_not_s4():
    """name_score == hold threshold routes past S4."""
    result = _route(signals(name_similarity_score=75.0), payment(), BASE_THRESHOLDS)
    assert result[0] != 4


def test_scenario_4_just_below_boundary():
    result = _route(signals(name_similarity_score=74.9), payment(), BASE_THRESHOLDS)
    assert result[0] == 4


def test_scenario_4_respects_custom_threshold():
    thresholds = {**BASE_THRESHOLDS, "name_match_hold": "80"}
    result = _route(signals(name_similarity_score=78.0), payment(), thresholds)
    assert result[0] == 4


# ---------------------------------------------------------------------------
# Scenario 3 — high amount variance
# ---------------------------------------------------------------------------

def test_scenario_3_variance_above_tolerance():
    result = _route(
        signals(name_similarity_score=95.0, amount_variance_pct=20.0),
        payment(),
        BASE_THRESHOLDS,
    )
    assert result[0] == 3
    assert "tier_3" in result[1]


def test_scenario_3_exactly_at_tolerance_is_not_s3():
    """variance == tolerance is not > tolerance — should not route to S3."""
    result = _route(
        signals(name_similarity_score=95.0, amount_variance_pct=2.0),
        payment(),
        BASE_THRESHOLDS,
    )
    assert result[0] != 3


def test_scenario_3_negative_variance_uses_absolute_value():
    """Underpayments (negative variance) route to S3 the same way overpayments do."""
    result = _route(
        signals(name_similarity_score=95.0, amount_variance_pct=-20.0),
        payment(),
        BASE_THRESHOLDS,
    )
    assert result[0] == 3


@pytest.mark.parametrize("variance,expected_tier", [
    (3.0, 2),
    (15.0, 2),
    (15.1, 3),
    (50.0, 3),
    (50.1, 4),
    (100.0, 4),
    (100.1, 5),
])
def test_scenario_3_decision_path_tiers(variance, expected_tier):
    result = _route(
        signals(name_similarity_score=95.0, amount_variance_pct=variance),
        payment(),
        BASE_THRESHOLDS,
    )
    assert result[0] == 3
    assert result[1] == f"scenario_3_tier_{expected_tier}"


def test_scenario_3_takes_priority_over_s1_s2():
    """High variance routes to S3 even if a valid policy reference exists."""
    result = _route(
        signals(name_similarity_score=95.0, amount_variance_pct=50.0),
        payment(extracted_policy_number="POL-99"),
        BASE_THRESHOLDS,
    )
    assert result[0] == 3


# ---------------------------------------------------------------------------
# Scenario 1 — strong policy match
# ---------------------------------------------------------------------------

def test_scenario_1_with_policy_reference():
    result = _route(
        signals(name_similarity_score=95.0, amount_variance_pct=0.0),
        payment(extracted_policy_number="POL-12345"),
        BASE_THRESHOLDS,
    )
    assert result == (1, "scenario_1_strong_policy_match")


def test_scenario_1_at_75_pct_name_score():
    """Name at hold boundary + policy ref → S1 (not S4)."""
    result = _route(
        signals(name_similarity_score=75.0, amount_variance_pct=0.0),
        payment(extracted_policy_number="POL-99"),
        BASE_THRESHOLDS,
    )
    assert result[0] == 1


# ---------------------------------------------------------------------------
# Scenario 2 — customer match, no policy reference
# ---------------------------------------------------------------------------

def test_scenario_2_no_policy_reference():
    result = _route(
        signals(name_similarity_score=95.0, amount_variance_pct=0.0),
        payment(extracted_policy_number=None),
        BASE_THRESHOLDS,
    )
    assert result == (2, "scenario_2_customer_match_no_policy")


def test_scenario_2_empty_string_policy_treated_as_absent():
    result = _route(
        signals(name_similarity_score=95.0, amount_variance_pct=0.0),
        payment(extracted_policy_number=""),
        BASE_THRESHOLDS,
    )
    assert result[0] == 2


# ---------------------------------------------------------------------------
# Integration — route_scenario() loads thresholds from real DB
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_route_scenario_integration(db):
    """Verifies threshold loading + routing work end-to-end with a real DB transaction."""
    await db.execute(text("""
        INSERT INTO configuration_thresholds (parameter_name, parameter_value, description)
        VALUES
            ('name_match_hold',      '75', 'test'),
            ('amount_tolerance_auto', '2', 'test')
        ON CONFLICT (parameter_name) DO UPDATE SET parameter_value = EXCLUDED.parameter_value
    """))

    pmt = {"payment_id": "PMT-TEST-01", "extracted_policy_number": "POL-99999"}
    sigs = {
        "is_duplicate_match": False,
        "name_similarity_score": 96.0,
        "amount_variance_pct": 0.0,
    }

    result = await route_scenario(pmt, sigs, db)

    assert result.scenario == 1
    assert result.decision_path == "scenario_1_strong_policy_match"
    assert "name_match_hold" in result.thresholds
