"""Tests for SLA service pure helpers (Phase 2)."""
from datetime import datetime, timedelta, timezone

import pytest

from app.services.sla import compute_due_date
from app.services.persist import _SLA_HOURS


class TestComputeDueDate:
    def _now(self):
        return datetime(2026, 5, 11, 12, 0, 0, tzinfo=timezone.utc)

    def test_default_sla_hours(self):
        now = self._now()
        due = compute_due_date(now)
        assert due == now + timedelta(hours=_SLA_HOURS)

    def test_default_sla_is_72_hours(self):
        now = self._now()
        due = compute_due_date(now)
        assert (due - now).total_seconds() == 72 * 3600

    def test_custom_sla_hours(self):
        now = self._now()
        due = compute_due_date(now, sla_hours=24)
        assert (due - now).total_seconds() == 24 * 3600

    def test_due_date_is_in_future(self):
        now = datetime.now(timezone.utc)
        due = compute_due_date(now)
        assert due > now

    def test_zero_sla_returns_same_time(self):
        now = self._now()
        due = compute_due_date(now, sla_hours=0)
        assert due == now

    def test_preserves_timezone(self):
        now = self._now()
        due = compute_due_date(now)
        assert due.tzinfo == timezone.utc

    def test_due_date_arithmetic(self):
        base = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        due = compute_due_date(base, sla_hours=72)
        assert due == datetime(2026, 1, 4, 0, 0, 0, tzinfo=timezone.utc)

    def test_large_sla_hours(self):
        now = self._now()
        due = compute_due_date(now, sla_hours=168)  # 1 week
        assert (due - now).days == 7
