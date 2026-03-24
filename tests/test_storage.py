"""Tests for storage helpers."""

from datetime import date

from yourcoverage.storage import week_label


class TestWeekLabel:
    def test_returns_iso_format(self):
        label = week_label(date(2026, 3, 24))
        assert label == "2026-W13"

    def test_current_week(self):
        label = week_label()
        assert label.startswith("20")
        assert "-W" in label
