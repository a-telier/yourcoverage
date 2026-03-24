"""Tests for CSV and JSON export."""

import csv
import json

from yourcoverage.aggregator import MonthlyMetrics
from yourcoverage.exporter import export_csv, export_json, export_errors
from yourcoverage.fetcher import ProfileResult


def _sample_metrics() -> list[MonthlyMetrics]:
    return [
        MonthlyMetrics(
            username="nike",
            year=2025,
            month=1,
            post_count=10,
            total_likes=5000,
            total_comments=500,
            avg_likes=500.0,
            avg_comments=50.0,
            engagement_rate=0.055,
            follower_count=100000,
        ),
        MonthlyMetrics(
            username="nike",
            year=2025,
            month=2,
            post_count=8,
            total_likes=4000,
            total_comments=400,
            avg_likes=500.0,
            avg_comments=50.0,
            engagement_rate=0.055,
            follower_count=100000,
        ),
    ]


def test_export_csv(tmp_path):
    metrics = _sample_metrics()
    path = export_csv(metrics, tmp_path)

    assert path.exists()
    assert path.suffix == ".csv"

    with open(path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 2
    assert rows[0]["username"] == "nike"
    assert rows[0]["post_count"] == "10"
    assert rows[0]["total_likes"] == "5000"


def test_export_json(tmp_path):
    metrics = _sample_metrics()
    path = export_json(metrics, tmp_path)

    assert path.exists()
    assert path.suffix == ".json"

    with open(path) as f:
        data = json.load(f)

    assert "nike" in data
    assert len(data["nike"]) == 2
    assert data["nike"][0]["month"] == 1
    assert data["nike"][0]["total_likes"] == 5000


def test_export_errors_with_errors(tmp_path):
    results = [
        ProfileResult(username="ok_user"),
        ProfileResult(username="bad_user", error="Profile is private"),
    ]
    path = export_errors(results, tmp_path)
    assert path is not None
    content = path.read_text()
    assert "bad_user: Profile is private" in content


def test_export_errors_no_errors(tmp_path):
    results = [ProfileResult(username="ok_user")]
    path = export_errors(results, tmp_path)
    assert path is None
