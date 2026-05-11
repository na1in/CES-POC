"""Tests for config change-request pure helpers (Phase 3)."""
import pytest

from app.routers.config import (
    ChangeRequestBody,
    RejectBody,
    can_deploy,
    can_rollback,
)


class TestCanDeploy:
    def test_approved_can_deploy(self):
        assert can_deploy({"status": "approved"}) is True

    def test_pending_cannot_deploy(self):
        assert can_deploy({"status": "pending"}) is False

    def test_rejected_cannot_deploy(self):
        assert can_deploy({"status": "rejected"}) is False

    def test_deployed_cannot_deploy_again(self):
        assert can_deploy({"status": "deployed"}) is False

    def test_rolled_back_cannot_deploy(self):
        assert can_deploy({"status": "rolled_back"}) is False


class TestCanRollback:
    def test_deployed_can_rollback(self):
        assert can_rollback({"status": "deployed"}) is True

    def test_pending_cannot_rollback(self):
        assert can_rollback({"status": "pending"}) is False

    def test_approved_cannot_rollback(self):
        assert can_rollback({"status": "approved"}) is False

    def test_rejected_cannot_rollback(self):
        assert can_rollback({"status": "rejected"}) is False

    def test_already_rolled_back_cannot_rollback(self):
        assert can_rollback({"status": "rolled_back"}) is False


class TestChangeRequestBody:
    def test_valid_body(self):
        body = ChangeRequestBody(
            parameter_name="name_match_auto_apply",
            proposed_value="92",
            rationale="Reducing false positives in auto-apply path",
        )
        assert body.parameter_name == "name_match_auto_apply"

    def test_empty_rationale_raises(self):
        with pytest.raises(Exception):
            ChangeRequestBody(
                parameter_name="name_match_auto_apply",
                proposed_value="92",
                rationale="   ",
            )

    def test_projected_impact_optional(self):
        body = ChangeRequestBody(
            parameter_name="amount_tolerance_auto",
            proposed_value="3",
            rationale="Allow slightly larger variance for auto-apply",
        )
        assert body.projected_impact is None


class TestRejectBody:
    def test_valid_comment(self):
        body = RejectBody(comment="Proposed change too aggressive for current period")
        assert body.comment.startswith("Proposed")

    def test_empty_comment_raises(self):
        with pytest.raises(Exception):
            RejectBody(comment="")

    def test_whitespace_comment_raises(self):
        with pytest.raises(Exception):
            RejectBody(comment="   \n")


class TestGovernanceHelpers:
    def test_valid_export_scope(self):
        from app.routers.governance import is_valid_export_scope
        assert is_valid_export_scope("decisions") is True
        assert is_valid_export_scope("overrides") is True
        assert is_valid_export_scope("config_changes") is True
        assert is_valid_export_scope("all") is True

    def test_invalid_export_scope(self):
        from app.routers.governance import is_valid_export_scope
        assert is_valid_export_scope("payments") is False
        assert is_valid_export_scope("") is False
        assert is_valid_export_scope("ALL") is False
