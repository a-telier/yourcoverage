"""Export metrics to CSV and JSON."""

import csv
import json
from collections import defaultdict
from dataclasses import asdict
from datetime import date
from pathlib import Path

from .aggregator import MonthlyMetrics
from .fetcher import ProfileResult


def _ensure_dir(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)


def _timestamp() -> str:
    return date.today().isoformat()


def export_csv(metrics: list[MonthlyMetrics], output_dir: Path) -> Path:
    """Write metrics to a CSV file."""
    _ensure_dir(output_dir)
    filepath = output_dir / f"competitor_report_{_timestamp()}.csv"

    fieldnames = [
        "username",
        "year",
        "month",
        "post_count",
        "total_likes",
        "total_comments",
        "avg_likes",
        "avg_comments",
        "engagement_rate",
        "follower_count",
    ]

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for m in metrics:
            writer.writerow(asdict(m))

    return filepath


def export_json(metrics: list[MonthlyMetrics], output_dir: Path) -> Path:
    """Write metrics to a JSON file, grouped by username."""
    _ensure_dir(output_dir)
    filepath = output_dir / f"competitor_report_{_timestamp()}.json"

    grouped: dict[str, list[dict]] = defaultdict(list)
    for m in metrics:
        entry = asdict(m)
        username = entry.pop("username")
        grouped[username].append(entry)

    with open(filepath, "w") as f:
        json.dump(grouped, f, indent=2)

    return filepath


def export_errors(results: list[ProfileResult], output_dir: Path) -> Path | None:
    """Write error log for failed profiles. Returns None if no errors."""
    errors = [(r.username, r.error) for r in results if r.error]
    if not errors:
        return None

    _ensure_dir(output_dir)
    filepath = output_dir / f"errors_{_timestamp()}.log"

    with open(filepath, "w") as f:
        for username, error in errors:
            f.write(f"{username}: {error}\n")

    return filepath
