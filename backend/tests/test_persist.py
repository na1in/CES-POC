"""Tests for the persist layer pure helpers (CES-23)."""
import pytest

from app.services.persist import _target_status


class TestTargetStatus:
    def test_apply_no_approval_is_applied(self):
        assert _target_status("APPLY", False) == "applied"

    def test_apply_with_approval_is_held(self):
        assert _target_status("APPLY", True) == "held"

    def test_hold_is_held(self):
        assert _target_status("HOLD", True) == "held"

    def test_hold_no_approval_still_held(self):
        # HOLD always becomes held regardless of approval flag
        assert _target_status("HOLD", False) == "held"

    def test_escalate_is_escalated(self):
        assert _target_status("ESCALATE", True) == "escalated"

    def test_escalate_no_approval_still_escalated(self):
        assert _target_status("ESCALATE", False) == "escalated"

    @pytest.mark.parametrize("rec,approval,expected", [
        ("APPLY",    False, "applied"),
        ("APPLY",    True,  "held"),
        ("HOLD",     True,  "held"),
        ("HOLD",     False, "held"),
        ("ESCALATE", True,  "escalated"),
        ("ESCALATE", False, "escalated"),
    ])
    def test_matrix(self, rec, approval, expected):
        assert _target_status(rec, approval) == expected
