from app.services.signals.amount import compute_historical_consistency
from app.services.signals.matching import (
    compute_customer_match_confidence,
    compute_policy_match_confidence,
)


# ══════════════════════════════════════════════════════════════════════════════
# Policy Match Confidence
# ══════════════════════════════════════════════════════════════════════════════

def test_policy_confidence_perfect_match():
    result = compute_policy_match_confidence(
        name_similarity_score=95.0,
        extracted_policy_number="POL-00001",
        actual_policy_number="POL-00001",
        amount_variance_pct=1.0,
    )
    # name(95*0.4=38) + policy(100*0.4=40) + amount(100*0.2=20) = 98
    assert result == 98.0


def test_policy_confidence_no_policy_candidate():
    result = compute_policy_match_confidence(
        name_similarity_score=95.0,
        extracted_policy_number="POL-00001",
        actual_policy_number=None,
        amount_variance_pct=1.0,
    )
    assert result == 0.0


def test_policy_confidence_policy_number_mismatch():
    result = compute_policy_match_confidence(
        name_similarity_score=95.0,
        extracted_policy_number="POL-00002",
        actual_policy_number="POL-00001",
        amount_variance_pct=1.0,
    )
    # name(95*0.4=38) + policy(0*0.4=0) + amount(100*0.2=20) = 58
    assert result == 58.0


def test_policy_confidence_no_extracted_policy_number():
    result = compute_policy_match_confidence(
        name_similarity_score=80.0,
        extracted_policy_number=None,
        actual_policy_number="POL-00001",
        amount_variance_pct=1.0,
    )
    # name(80*0.4=32) + policy(0) + amount(100*0.2=20) = 52
    assert result == 52.0


def test_policy_confidence_high_variance_reduces_score():
    result = compute_policy_match_confidence(
        name_similarity_score=95.0,
        extracted_policy_number="POL-00001",
        actual_policy_number="POL-00001",
        amount_variance_pct=10.0,  # >2% — no amount score
    )
    # name(95*0.4=38) + policy(100*0.4=40) + amount(0) = 78
    assert result == 78.0


def test_policy_confidence_case_insensitive_policy_match():
    result = compute_policy_match_confidence(
        name_similarity_score=90.0,
        extracted_policy_number="pol-00001",
        actual_policy_number="POL-00001",
        amount_variance_pct=0.5,
    )
    # name(90*0.4=36) + policy(100*0.4=40) + amount(100*0.2=20) = 96
    assert result == 96.0


# ══════════════════════════════════════════════════════════════════════════════
# Customer Match Confidence
# ══════════════════════════════════════════════════════════════════════════════

def test_customer_confidence_all_signals_match():
    result = compute_customer_match_confidence(
        name_similarity_score=95.0,
        account_match=True,
        historical_match=True,
    )
    # name(95*0.6=57) + account(100*0.2=20) + historical(100*0.2=20) = 97
    assert result == 97.0


def test_customer_confidence_name_only():
    result = compute_customer_match_confidence(
        name_similarity_score=90.0,
        account_match=False,
        historical_match=False,
    )
    assert result == 54.0  # 90 * 0.6


def test_customer_confidence_low_name_high_supporting():
    result = compute_customer_match_confidence(
        name_similarity_score=60.0,
        account_match=True,
        historical_match=True,
    )
    # 60*0.6 + 100*0.2 + 100*0.2 = 36 + 20 + 20 = 76
    assert result == 76.0


def test_customer_confidence_zero_name_no_signals():
    result = compute_customer_match_confidence(
        name_similarity_score=0.0,
        account_match=False,
        historical_match=False,
    )
    assert result == 0.0


# ══════════════════════════════════════════════════════════════════════════════
# Historical Consistency
# ══════════════════════════════════════════════════════════════════════════════

def test_historical_consistency_no_history():
    assert compute_historical_consistency(150000, []) == 100.0


def test_historical_consistency_one_record():
    assert compute_historical_consistency(150000, [150000]) == 100.0


def test_historical_consistency_exact_match():
    history = [150000, 150000, 150000, 150000]
    assert compute_historical_consistency(150000, history) == 100.0


def test_historical_consistency_identical_history_no_stdev():
    # All identical → stdev=0, should not divide by zero
    history = [150000] * 6
    assert compute_historical_consistency(200000, history) == 100.0


def test_historical_consistency_slight_outlier():
    history = [150000, 151000, 149000, 150500, 149500, 150000]
    result = compute_historical_consistency(152000, history)
    # Small deviation from mean should still score reasonably well
    assert result > 50.0


def test_historical_consistency_strong_outlier():
    history = [150000, 150000, 150000, 150000, 150000, 150000]
    # $500 difference with stdev near 0 → but stdev=0 guard returns 100
    # Use varied history so stdev > 0
    history = [140000, 150000, 160000, 145000, 155000, 150000]
    result = compute_historical_consistency(300000, history)  # 3x the average
    assert result < 50.0


def test_historical_consistency_score_floored_at_zero():
    history = [100000, 100100, 99900, 100050, 99950, 100000]
    result = compute_historical_consistency(1000000, history)  # extreme outlier
    assert result == 0.0
