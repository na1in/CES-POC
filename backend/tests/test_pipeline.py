"""Tests for the pipeline orchestrator pure helpers (CES-24)."""
import pytest
import anthropic
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from unittest.mock import MagicMock

from app.services.pipeline import _is_retryable, _build_context


# ─────────────────────────────────────────────────────────────────────────────
# _is_retryable
# ─────────────────────────────────────────────────────────────────────────────

class TestIsRetryable:
    def test_integrity_error_not_retryable(self):
        exc = IntegrityError("constraint violation", params={}, orig=Exception())
        assert _is_retryable(exc) is False

    def test_programming_error_not_retryable(self):
        exc = ProgrammingError("bad sql", params={}, orig=Exception())
        assert _is_retryable(exc) is False

    def test_value_error_not_retryable(self):
        assert _is_retryable(ValueError("bad input")) is False

    def test_operational_error_retryable(self):
        exc = OperationalError("db timeout", params={}, orig=Exception())
        assert _is_retryable(exc) is True

    def test_claude_timeout_retryable(self):
        exc = anthropic.APITimeoutError(request=MagicMock())
        assert _is_retryable(exc) is True

    def test_claude_rate_limit_retryable(self):
        exc = anthropic.RateLimitError(
            message="rate limit",
            response=MagicMock(headers={}),
            body={},
        )
        assert _is_retryable(exc) is True

    def test_claude_connection_error_retryable(self):
        exc = anthropic.APIConnectionError(request=MagicMock())
        assert _is_retryable(exc) is True

    def test_unknown_exception_not_retryable(self):
        assert _is_retryable(RuntimeError("unexpected")) is False

    def test_plain_exception_not_retryable(self):
        assert _is_retryable(Exception("generic")) is False


# ─────────────────────────────────────────────────────────────────────────────
# _build_context
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildContext:
    def _customer(self):
        return {"customer_name": "Jane Doe", "status": "active"}

    def _policy(self):
        return {"policy_number": "POL-12345", "premium_amount": 50000}

    def _active_policies(self):
        return [
            {"policy_id": "POL-12345", "policy_number": "POL-12345", "premium_amount_cents": 50000},
            {"policy_id": "POL-99999", "policy_number": "POL-99999", "premium_amount_cents": 30000},
        ]

    def test_context_with_policy(self):
        ctx = _build_context(self._customer(), "CUST-001", self._policy(), self._active_policies())
        assert ctx["customer_id"] == "CUST-001"
        assert ctx["customer_name"] == "Jane Doe"
        assert ctx["policy_id"] == "POL-12345"
        assert ctx["policy_number"] == "POL-12345"
        assert ctx["active_policy_count"] == 2
        assert len(ctx["active_policies"]) == 2

    def test_context_without_policy(self):
        ctx = _build_context(self._customer(), "CUST-001", None, [])
        assert ctx["policy_id"] is None
        assert ctx["policy_number"] is None
        assert ctx["active_policy_count"] == 0

    def test_context_no_customer_id(self):
        ctx = _build_context(self._customer(), None, None, [])
        assert ctx["customer_id"] is None

    def test_active_policy_count_matches_list_length(self):
        for n in (0, 1, 3):
            policies = [{"policy_id": f"P{i}", "policy_number": f"P{i}", "premium_amount_cents": 1000}
                        for i in range(n)]
            ctx = _build_context(self._customer(), "CUST-001", None, policies)
            assert ctx["active_policy_count"] == n
