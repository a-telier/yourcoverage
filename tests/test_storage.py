"""Tests for weekly data storage."""

import json
from datetime import date

from yourcoverage.storage import (
    week_label,
    save_snapshot,
    load_snapshot,
    resolve_week_range,
    list_weeks,
)


class TestWeekLabel:
    def test_returns_iso_format(self):
        label = week_label(date(2026, 3, 24))
        assert label == "2026-W13"

    def test_current_week(self):
        label = week_label()
        assert label.startswith("20")
        assert "-W" in label


class TestSaveLoadSnapshot:
    def test_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setattr("yourcoverage.storage.DATA_DIR", tmp_path)
        data = {"profile": {"followers": 1000}, "posts": []}
        save_snapshot("testuser", data, "2026-W12")
        loaded = load_snapshot("testuser", "2026-W12")
        assert loaded["profile"]["followers"] == 1000

    def test_missing_snapshot(self, tmp_path, monkeypatch):
        monkeypatch.setattr("yourcoverage.storage.DATA_DIR", tmp_path)
        assert load_snapshot("nouser", "2026-W99") is None


class TestResolveWeekRange:
    def test_latest_n(self, tmp_path, monkeypatch):
        monkeypatch.setattr("yourcoverage.storage.DATA_DIR", tmp_path)
        for w in ["2026-W09", "2026-W10", "2026-W11", "2026-W12"]:
            (tmp_path / w).mkdir()
        result = resolve_week_range("latest-2")
        assert result == ["2026-W11", "2026-W12"]

    def test_short_range(self, tmp_path, monkeypatch):
        monkeypatch.setattr("yourcoverage.storage.DATA_DIR", tmp_path)
        for w in ["2026-W09", "2026-W10", "2026-W11", "2026-W12"]:
            (tmp_path / w).mkdir()
        result = resolve_week_range("10-12")
        assert result == ["2026-W10", "2026-W11", "2026-W12"]

    def test_all(self, tmp_path, monkeypatch):
        monkeypatch.setattr("yourcoverage.storage.DATA_DIR", tmp_path)
        for w in ["2026-W09", "2026-W10"]:
            (tmp_path / w).mkdir()
        result = resolve_week_range("all")
        assert len(result) == 2

    def test_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("yourcoverage.storage.DATA_DIR", tmp_path)
        assert resolve_week_range("latest-4") == []
