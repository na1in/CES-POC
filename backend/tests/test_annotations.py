"""Tests for annotation pure helpers (Phase 2)."""
import pytest

from app.routers.annotations import (
    AnnotationBody,
    contact_record_triggers_pending,
    requires_contact_fields,
)


class TestRequiresContactFields:
    def test_contact_record_requires_fields(self):
        assert requires_contact_fields("contact_record") is True

    def test_case_note_does_not(self):
        assert requires_contact_fields("case_note") is False

    def test_override_reason_does_not(self):
        assert requires_contact_fields("override_reason") is False

    def test_investigation_note_does_not(self):
        assert requires_contact_fields("investigation_note") is False


class TestContactRecordTriggersPending:
    def test_escalated_triggers(self):
        assert contact_record_triggers_pending("escalated") is True

    def test_held_does_not_trigger(self):
        assert contact_record_triggers_pending("held") is False

    def test_pending_sender_response_does_not_trigger(self):
        # Already in that state — no transition needed
        assert contact_record_triggers_pending("pending_sender_response") is False

    def test_applied_does_not_trigger(self):
        assert contact_record_triggers_pending("applied") is False

    def test_received_does_not_trigger(self):
        assert contact_record_triggers_pending("received") is False


class TestAnnotationBodyValidation:
    def test_valid_case_note(self):
        body = AnnotationBody(annotation_type="case_note", content="Looks good")
        assert body.annotation_type == "case_note"

    def test_invalid_type_raises(self):
        with pytest.raises(Exception):
            AnnotationBody(annotation_type="unknown_type", content="test")

    def test_empty_content_raises(self):
        with pytest.raises(Exception):
            AnnotationBody(annotation_type="case_note", content="   ")

    def test_whitespace_only_content_raises(self):
        with pytest.raises(Exception):
            AnnotationBody(annotation_type="case_note", content="\n\t")

    def test_contact_record_without_method_is_valid_model(self):
        # Business rule validation happens in the endpoint, not the model
        body = AnnotationBody(annotation_type="contact_record", content="Called sender")
        assert body.contact_method is None

    def test_contact_record_with_method(self):
        body = AnnotationBody(
            annotation_type="contact_record",
            content="Called sender",
            contact_method="phone",
            contact_outcome="reached",
            contacted_party="John Doe",
        )
        assert body.contact_method == "phone"
        assert body.contact_outcome == "reached"

    @pytest.mark.parametrize("atype", ["case_note", "override_reason", "contact_record", "investigation_note"])
    def test_all_valid_types_accepted(self, atype):
        body = AnnotationBody(annotation_type=atype, content="some content")
        assert body.annotation_type == atype
