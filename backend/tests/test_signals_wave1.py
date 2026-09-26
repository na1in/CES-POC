from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.signals.amount import compute_amount_variance
from app.services.signals.duplicate import compute_duplicate
from app.services.signals.matching import compute_name_similarity, normalise_name_pair
from app.services.signals.temporal import compute_timing


# ══════════════════════════════════════════════════════════════════════════════
# Name Similarity
# ══════════════════════════════════════════════════════════════════════════════

async def test_name_exact_match():
    result = await compute_name_similarity("Robert Johnson", "Robert Johnson")
    assert result["name_similarity_score"] == 100.0
    assert result["used_llm"] is False


async def test_name_clear_mismatch_skips_llm():
    with patch("app.services.signals.matching._get_client") as mock_client:
        result = await compute_name_similarity("Robert Johnson", "Zhang Wei")
        mock_client.assert_not_called()
    assert result["name_similarity_score"] < 70.0
    assert result["used_llm"] is False


async def test_name_clear_match_skips_llm():
    with patch("app.services.signals.matching._get_client") as mock_client:
        result = await compute_name_similarity("Robert Johnson", "Robert Johnston")
        mock_client.assert_not_called()
    assert result["name_similarity_score"] > 92.0
    assert result["used_llm"] is False


async def test_name_gray_zone_calls_llm():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"score": 88, "reasoning": "Rob is short for Robert"}'
    with patch("app.services.signals.matching._get_client") as mock_client:
        mock_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response)
        result = await compute_name_similarity("Rob Johnson", "Robert Johnson")
    assert result["used_llm"] is True
    assert result["llm_score"] == 88.0
    assert result["name_similarity_score"] >= 88.0


async def test_name_gray_zone_llm_timeout_falls_back_to_deterministic():
    with patch("app.services.signals.matching._get_client") as mock_client:
        mock_client.return_value.messages.create = AsyncMock(side_effect=TimeoutError("timeout"))
        result = await compute_name_similarity("Rob Johnson", "Robert Johnson")
    assert result["used_llm"] is False
    assert result["llm_score"] is None
    assert result["name_similarity_score"] == result["deterministic_score"]


async def test_name_final_score_is_max_of_deterministic_and_llm():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"score": 95, "reasoning": "same person"}'
    with patch("app.services.signals.matching._get_client") as mock_client:
        mock_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response)
        result = await compute_name_similarity("Rob Johnson", "Robert Johnson")
    assert result["name_similarity_score"] == max(result["deterministic_score"], 95.0)


async def test_name_result_contains_all_breakdown_fields():
    result = await compute_name_similarity("Alice Smith", "Alice Smith")
    for field in ["jaro_winkler_score", "levenshtein_score", "soundex_match",
                  "deterministic_score", "used_llm", "llm_score", "name_similarity_score"]:
        assert field in result, f"Missing field: {field}"


# ══════════════════════════════════════════════════════════════════════════════
# Amount Variance
# ══════════════════════════════════════════════════════════════════════════════

def test_amount_exact_match():
    result = compute_amount_variance(150000, 150000)
    assert result["amount_variance_pct"] == 0.0
    assert result["is_overpayment"] is False
    assert result["is_underpayment"] is False
    assert result["difference_amount"] == 0


def test_amount_overpayment():
    result = compute_amount_variance(160000, 150000)
    assert result["is_overpayment"] is True
    assert result["is_underpayment"] is False
    assert result["difference_amount"] == 10000
    assert round(result["amount_variance_pct"], 2) == 6.67


def test_amount_underpayment():
    result = compute_amount_variance(140000, 150000)
    assert result["is_underpayment"] is True
    assert result["is_overpayment"] is False
    assert result["difference_amount"] == -10000


def test_amount_variance_within_2_percent():
    result = compute_amount_variance(151000, 150000)
    assert result["amount_variance_pct"] < 2.0


def test_amount_variance_no_premium():
    result = compute_amount_variance(150000, 0)
    assert result["amount_variance_pct"] is None
    assert result["difference_amount"] is None


# ══════════════════════════════════════════════════════════════════════════════
# Payment Timing
# ══════════════════════════════════════════════════════════════════════════════

def _pmt(days_offset: int) -> datetime:
    base = date(2026, 4, 15)
    return datetime(2026, 4, 15 + days_offset, tzinfo=timezone.utc)


def test_timing_excellent_on_due_date():
    result = compute_timing(
        payment_date=datetime(2026, 4, 15, tzinfo=timezone.utc),
        next_due_date=date(2026, 4, 15),
        last_payment_date=None,
    )
    assert result["payment_timing_quality"] == "excellent"


def test_timing_excellent_early():
    result = compute_timing(
        payment_date=datetime(2026, 4, 10, tzinfo=timezone.utc),
        next_due_date=date(2026, 4, 15),
        last_payment_date=None,
    )
    assert result["payment_timing_quality"] == "excellent"


def test_timing_good():
    result = compute_timing(
        payment_date=datetime(2026, 4, 18, tzinfo=timezone.utc),
        next_due_date=date(2026, 4, 15),
        last_payment_date=None,
    )
    assert result["payment_timing_quality"] == "good"


def test_timing_acceptable():
    result = compute_timing(
        payment_date=datetime(2026, 4, 25, tzinfo=timezone.utc),
        next_due_date=date(2026, 4, 15),
        last_payment_date=None,
    )
    assert result["payment_timing_quality"] == "acceptable"


def test_timing_poor_very_late():
    result = compute_timing(
        payment_date=datetime(2026, 5, 10, tzinfo=timezone.utc),
        next_due_date=date(2026, 4, 15),
        last_payment_date=None,
    )
    assert result["payment_timing_quality"] == "poor"


def test_timing_no_due_date_defaults_to_poor():
    result = compute_timing(
        payment_date=datetime(2026, 4, 15, tzinfo=timezone.utc),
        next_due_date=None,
        last_payment_date=None,
    )
    assert result["payment_timing_quality"] == "poor"


def test_timing_days_since_last_payment():
    last = datetime(2026, 3, 15, tzinfo=timezone.utc)
    current = datetime(2026, 4, 15, tzinfo=timezone.utc)
    result = compute_timing(current, date(2026, 4, 15), last)
    assert result["days_since_last_payment"] == 31


def test_timing_no_last_payment():
    result = compute_timing(datetime(2026, 4, 15, tzinfo=timezone.utc), date(2026, 4, 15), None)
    assert result["days_since_last_payment"] is None


# ══════════════════════════════════════════════════════════════════════════════
# Duplicate Detection
# ══════════════════════════════════════════════════════════════════════════════

NOW = datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc)


async def _insert_prior_payment(
    db, payment_id: str, *, sender_name: str, sender_account: str | None, payment_method: str,
    reference: str | None, amount: int = 150000, hours_before: float = 2,
) -> None:
    from sqlalchemy import text
    await db.execute(text("""
        INSERT INTO payments (payment_id, amount, sender_name, sender_account,
            payment_method, payment_date, reference_field_1, status, created_timestamp)
        VALUES (:payment_id, :amount, :sender_name, :sender_account,
            :payment_method, :payment_date, :reference, 'held', :now)
    """), {"payment_id": payment_id, "amount": amount, "sender_name": sender_name,
           "sender_account": sender_account, "payment_method": payment_method, "reference": reference,
           "payment_date": NOW - timedelta(hours=hours_before), "now": NOW})


async def test_duplicate_exact_match(client, db):
    await _insert_prior_payment(db, "PMT-DUP-001", sender_name="Robert Johnson", sender_account="ACC-10001",
                                payment_method="ACH", reference="POL-DUP-001")

    result = await compute_duplicate(
        db=db,
        payment_id="PMT-DUP-002",
        sender_name="Robert Johnson",
        reference="POL-DUP-001",
        payment_method="ACH",
        payment_date=NOW,
        amount=150000,
    )
    assert result["is_duplicate_match"] is True
    assert result["duplicate_payment_id"] == "PMT-DUP-001"
    assert result["duplicate_amount_difference"] == 0
    assert result["hours_since_duplicate"] <= 3.0


async def test_duplicate_within_tolerance(client, db):
    await _insert_prior_payment(db, "PMT-DUP-003", sender_name="Jane Smith", sender_account="ACC-20001",
                                payment_method="Check", reference="POL-DUP-003", hours_before=10)

    result = await compute_duplicate(
        db=db,
        payment_id="PMT-DUP-004",
        sender_name="Jane Smith",
        reference="POL-DUP-003",
        payment_method="Check",
        payment_date=NOW,
        amount=150150,  # $1.50 difference — within $2 tolerance
    )
    assert result["is_duplicate_match"] is True
    assert result["duplicate_amount_difference"] == 150


async def test_duplicate_outside_tolerance(client, db):
    await _insert_prior_payment(db, "PMT-DUP-005", sender_name="Tom Brown", sender_account="ACC-30001",
                                payment_method="Wire", reference="POL-DUP-005", hours_before=5)

    result = await compute_duplicate(
        db=db,
        payment_id="PMT-DUP-006",
        sender_name="Tom Brown",
        reference="POL-DUP-005",
        payment_method="Wire",
        payment_date=NOW,
        amount=155000,  # $50 difference — outside tolerance
    )
    assert result["is_duplicate_match"] is False


async def test_duplicate_outside_time_window(client, db):
    await _insert_prior_payment(db, "PMT-DUP-007", sender_name="Sara Lee", sender_account="ACC-40001",
                                payment_method="ACH", reference="POL-DUP-007", hours_before=80)  # 80hrs > 72hr window

    result = await compute_duplicate(
        db=db,
        payment_id="PMT-DUP-008",
        sender_name="Sara Lee",
        reference="POL-DUP-007",
        payment_method="ACH",
        payment_date=NOW,
        amount=150000,
    )
    assert result["is_duplicate_match"] is False


async def test_duplicate_no_match(client, db):
    result = await compute_duplicate(
        db=db,
        payment_id="PMT-DUP-999",
        sender_name="Nobody Known",
        reference="POL-NONE-999",
        payment_method="ACH",
        payment_date=datetime(2026, 4, 20, tzinfo=timezone.utc),
        amount=150000,
    )
    assert result["is_duplicate_match"] is False
    assert result["duplicate_payment_id"] is None


async def test_duplicate_matches_regardless_of_sender_account(client, db):
    # Spec (Scenario 5): sender, method, policy reference and amount decide a duplicate — the account does not.
    await _insert_prior_payment(db, "PMT-DUP-010", sender_name="Anya Petrova", sender_account="ACC-93001",
                                payment_method="ACH", reference="POL-DUP-010")

    result = await compute_duplicate(
        db=db, payment_id="PMT-DUP-011", sender_name="Anya Petrova", reference="POL-DUP-010",
        payment_method="ACH", payment_date=NOW, amount=150000,
    )
    assert result["is_duplicate_match"] is True
    assert result["duplicate_payment_id"] == "PMT-DUP-010"


async def test_duplicate_different_reference_is_not_a_match(client, db):
    # Same sender, account, method and amount, but a different policy reference: two policies paid, not one duplicated.
    await _insert_prior_payment(db, "PMT-DUP-012", sender_name="Hiroshi Sato", sender_account="ACC-93003",
                                payment_method="ACH", reference="POL-DUP-012")

    result = await compute_duplicate(
        db=db, payment_id="PMT-DUP-013", sender_name="Hiroshi Sato", reference="POL-DUP-013",
        payment_method="ACH", payment_date=NOW, amount=150000,
    )
    assert result["is_duplicate_match"] is False


async def test_duplicate_matches_when_neither_payment_has_a_reference(client, db):
    await _insert_prior_payment(db, "PMT-DUP-014", sender_name="Reference Less", sender_account=None,
                                payment_method="Check", reference=None)

    result = await compute_duplicate(
        db=db, payment_id="PMT-DUP-015", sender_name="Reference Less", reference=None,
        payment_method="Check", payment_date=NOW, amount=150000,
    )
    assert result["is_duplicate_match"] is True


# ── Middle initials ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("sender, customer, expected_pair", [
    ("Boris P. Ulker", "Boris Ulker", ("boris ulker", "boris ulker")),
    ("Boris Ulker", "Boris P. Ulker", ("boris ulker", "boris ulker")),   # either side
    ("John A Smith", "John Smith", ("john smith", "john smith")),        # no period
    ("Smith, John A.", "John Smith", ("smith john", "john smith")),      # punctuation is dropped
    # an initial that matches a token in the other name is evidence, so it is kept
    ("Robert J Miller", "Robert James Miller", ("robert j miller", "robert james miller")),
    ("Robert J Miller", "Robert J Miller", ("robert j miller", "robert j miller")),
    # an initial equal to the first letter of a name the other side ALREADY has in full is still just an extra initial
    ("Matthew M. Estevez", "Matthew Estevez", ("matthew estevez", "matthew estevez")),
    ("Cesar C. Delahaye", "Cesar Delahaye", ("cesar delahaye", "cesar delahaye")),
    ("Salome S. Armenta", "Salome Armenta", ("salome armenta", "salome armenta")),
    # a different initial on each side is not dropped
    ("John B Smith", "John A Smith", ("john b smith", "john a smith")),
    # a name is never reduced to nothing
    ("J", "K", ("j", "k")),
])
def test_normalise_name_pair(sender, customer, expected_pair):
    assert normalise_name_pair(sender, customer) == expected_pair


async def test_middle_initial_scores_as_a_strong_match():
    """Spec: "John A Smith" vs "John Smith" is a strong match. Un-normalised, "Boris P. Ulker" scored ~79 (HOLD)."""
    for sender, customer in [("Boris P. Ulker", "Boris Ulker"), ("Andrew N. Benson", "Andrew Benson"),
                             ("Karan R. Wydrych", "Karan Wydrych"), ("John A. Smith", "John Smith"),
                             ("Matthew M. Estevez", "Matthew Estevez"), ("Cesar C. Delahaye", "Cesar Delahaye")]:
        result = await compute_name_similarity(sender, customer)
        assert result["deterministic_score"] > 90.0, (sender, result["deterministic_score"])
        assert result["used_llm"] is False  # above the gray zone: no LLM needed


async def test_conflicting_initials_are_not_treated_as_the_same_person():
    same = await compute_name_similarity("John A Smith", "John A Smith")
    different = await compute_name_similarity("John B Smith", "John A Smith")
    assert different["deterministic_score"] < same["deterministic_score"]


async def test_nicknames_are_not_expanded():
    """Deliberate: whether "Bob" is "Robert" is a business decision, not a string rule."""
    result = await compute_name_similarity("Bob Miller", "Robert Miller")
    assert result["deterministic_score"] < 70.0


# ── Duplicate check counts a payment that failed processing ──────────────────────────────────────────────────

async def test_duplicate_matches_a_payment_that_failed_processing(client, db):
    """A processing_failed payment is money that arrived; an identical one 2 hours later is still a duplicate."""
    from sqlalchemy import text
    await _insert_prior_payment(db, "PMT-DUP-PF1", sender_name="Robert Johnson", sender_account="ACC-10001",
                                payment_method="ACH", reference="POL-DUP-PF1")
    await db.execute(text("UPDATE payments SET status = 'processing_failed' WHERE payment_id = 'PMT-DUP-PF1'"))

    result = await compute_duplicate(db=db, payment_id="PMT-DUP-PF2", sender_name="Robert Johnson",
                                     reference="POL-DUP-PF1", payment_method="ACH", payment_date=NOW, amount=150000)
    assert result["is_duplicate_match"] is True
    assert result["duplicate_payment_id"] == "PMT-DUP-PF1"


async def test_duplicate_ignores_a_returned_payment(client, db):
    from sqlalchemy import text
    await _insert_prior_payment(db, "PMT-DUP-RT1", sender_name="Robert Johnson", sender_account="ACC-10001",
                                payment_method="ACH", reference="POL-DUP-RT1")
    await db.execute(text("UPDATE payments SET status = 'returned' WHERE payment_id = 'PMT-DUP-RT1'"))

    result = await compute_duplicate(db=db, payment_id="PMT-DUP-RT2", sender_name="Robert Johnson",
                                     reference="POL-DUP-RT1", payment_method="ACH", payment_date=NOW, amount=150000)
    assert result["is_duplicate_match"] is False


# ── Duplicate window: symmetric, bounded on both sides ───────────────────────────────────────────────────────

async def test_duplicate_ignores_a_payment_dated_long_after(client, db):
    """The window used to have no upper bound, so a payment dated months LATER counted as a 'prior' duplicate
    (hours_since_duplicate in the thousands). It is not within 72 hours."""
    await _insert_prior_payment(db, "PMT-DUP-LATE1", sender_name="Robert Johnson", sender_account=None,
                                payment_method="ACH", reference="POL-DUP-LATE", hours_before=-24 * 120)  # 120 days AFTER NOW

    result = await compute_duplicate(db=db, payment_id="PMT-DUP-LATE2", sender_name="Robert Johnson",
                                     reference="POL-DUP-LATE", payment_method="ACH", payment_date=NOW, amount=150000)
    assert result["is_duplicate_match"] is False


async def test_duplicate_window_is_symmetric(client, db):
    """A duplicate can be processed before the original: an identical payment dated 10 hours after is a match."""
    await _insert_prior_payment(db, "PMT-DUP-SYM1", sender_name="Robert Johnson", sender_account=None,
                                payment_method="ACH", reference="POL-DUP-SYM", hours_before=-10)

    result = await compute_duplicate(db=db, payment_id="PMT-DUP-SYM2", sender_name="Robert Johnson",
                                     reference="POL-DUP-SYM", payment_method="ACH", payment_date=NOW, amount=150000)
    assert result["is_duplicate_match"] is True
    assert result["hours_since_duplicate"] == 10.0


async def test_duplicate_a_newer_payment_with_a_different_amount_does_not_hide_the_real_duplicate(client, db):
    """LIMIT 1 used to pick the most recent same-sender payment before the amount check, so a newer $300 payment
    hid an older exact $1,500 duplicate."""
    await _insert_prior_payment(db, "PMT-DUP-HID1", sender_name="Robert Johnson", sender_account=None,
                                payment_method="ACH", reference="POL-DUP-HID", amount=150000, hours_before=30)
    await _insert_prior_payment(db, "PMT-DUP-HID2", sender_name="Robert Johnson", sender_account=None,
                                payment_method="ACH", reference="POL-DUP-HID", amount=30000, hours_before=1)

    result = await compute_duplicate(db=db, payment_id="PMT-DUP-HID3", sender_name="Robert Johnson",
                                     reference="POL-DUP-HID", payment_method="ACH", payment_date=NOW, amount=150000)
    assert result["is_duplicate_match"] is True
    assert result["duplicate_payment_id"] == "PMT-DUP-HID1"
