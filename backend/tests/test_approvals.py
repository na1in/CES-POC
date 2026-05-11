"""Tests for approval action helpers (CES-25/26)."""
import pytest
from fastapi import HTTPException

from app.routers.approvals import _assert_status


class TestAssertStatus:
    def _payment(self, status: str) -> dict:
        return {"payment_id": "PMT-001", "status": status, "amount": 10000}

    def test_allowed_status_passes(self):
        _assert_status(self._payment("held"), {"held"}, "approve")  # no exception

    def test_disallowed_status_raises_409(self):
        with pytest.raises(HTTPException) as exc_info:
            _assert_status(self._payment("applied"), {"held"}, "approve")
        assert exc_info.value.status_code == 409

    def test_error_message_contains_action(self):
        with pytest.raises(HTTPException) as exc_info:
            _assert_status(self._payment("escalated"), {"held"}, "approve")
        assert "approve" in exc_info.value.detail

    def test_error_message_contains_current_status(self):
        with pytest.raises(HTTPException) as exc_info:
            _assert_status(self._payment("returned"), {"held"}, "approve")
        assert "returned" in exc_info.value.detail

    def test_multiple_allowed_statuses_pass(self):
        allowed = {"escalated", "pending_sender_response"}
        _assert_status(self._payment("escalated"), allowed, "return")
        _assert_status(self._payment("pending_sender_response"), allowed, "return")

    def test_multiple_allowed_statuses_rejects_others(self):
        allowed = {"escalated", "pending_sender_response"}
        with pytest.raises(HTTPException):
            _assert_status(self._payment("held"), allowed, "return")

    def test_processing_failed_reprocessable(self):
        _assert_status(self._payment("processing_failed"), {"processing_failed"}, "reprocess")

    def test_received_not_approvable(self):
        with pytest.raises(HTTPException):
            _assert_status(self._payment("received"), {"held"}, "approve")

    def test_applied_not_rejectable(self):
        with pytest.raises(HTTPException):
            _assert_status(self._payment("applied"), {"held"}, "reject")

    @pytest.mark.parametrize("bad_status", ["received", "processing", "applied", "returned"])
    def test_non_held_cannot_approve(self, bad_status):
        with pytest.raises(HTTPException):
            _assert_status(self._payment(bad_status), {"held"}, "approve")

    @pytest.mark.parametrize("good_status", ["held", "escalated", "processing", "received"])
    def test_overridable_statuses(self, good_status):
        allowed = {"held", "escalated", "processing", "received"}
        _assert_status(self._payment(good_status), allowed, "override")
