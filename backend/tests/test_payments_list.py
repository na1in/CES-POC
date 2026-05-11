"""Tests for GET /api/payments pure helpers (CES-28)."""
import pytest

from app.routers.payments import _VALID_SORT, _DEFAULT_SORT


class TestSortMap:
    def test_confidence_score_sort(self):
        assert "confidence_score" in _VALID_SORT["confidence_score"]

    def test_has_risk_flags_sort(self):
        assert "has_risk_flags" in _VALID_SORT["has_risk_flags"]

    def test_payment_method_sort(self):
        assert "payment_method" in _VALID_SORT["payment_method"]

    def test_payment_date_sort(self):
        assert "payment_date" in _VALID_SORT["payment_date"]

    def test_unknown_sort_falls_back_to_default(self):
        result = _VALID_SORT.get("nonexistent_field", _DEFAULT_SORT)
        assert result == _DEFAULT_SORT

    def test_default_sort_is_payment_date_desc(self):
        assert "payment_date" in _DEFAULT_SORT
        assert "DESC" in _DEFAULT_SORT

    def test_all_valid_sort_keys(self):
        expected_keys = {"confidence_score", "has_risk_flags", "payment_method", "payment_date"}
        assert set(_VALID_SORT.keys()) == expected_keys

    def test_confidence_score_nulls_last(self):
        assert "NULLS LAST" in _VALID_SORT["confidence_score"]

    def test_has_risk_flags_nulls_last(self):
        assert "NULLS LAST" in _VALID_SORT["has_risk_flags"]

    def test_sort_values_use_table_aliases(self):
        # Ensure column references are qualified to avoid ambiguity in joins
        for key, clause in _VALID_SORT.items():
            assert "." in clause, f"Sort clause for '{key}' should use table alias"
