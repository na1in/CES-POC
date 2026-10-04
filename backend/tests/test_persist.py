"""Tests for the persist layer pure helpers (CES-23)."""
import pytest

from app.services.persist import _target_status


class TestTargetStatus:
    """Human approval is always required (CLAUDE.md, stage 4): whatever the AI recommends, the payment lands HELD for
    the analyst. APPLIED / ESCALATED happen only when a person approves / rejects."""

    @pytest.mark.parametrize("rec", ["APPLY", "HOLD", "ESCALATE"])
    @pytest.mark.parametrize("approval", [True, False])
    def test_every_recommendation_lands_held(self, rec, approval):
        assert _target_status(rec, approval) == "held"
