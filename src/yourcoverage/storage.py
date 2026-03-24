"""Weekly data storage: save/load JSON snapshots organized by week."""

import json
import shutil
from datetime import datetime, date
from pathlib import Path

DATA_DIR = Path("data/weekly")


def week_label(dt: date | None = None) -> str:
    """Return ISO week label like '2026-W12'."""
    if dt is None:
        dt = date.today()
    year, week, _ = dt.isocalendar()
    return f"{year}-W{week:02d}"


def week_dir(week: str | None = None) -> Path:
    """Return the directory for a given week label."""
    if week is None:
        week = week_label()
    return DATA_DIR / week


def save_snapshot(username: str, data: dict, week: str | None = None) -> Path:
    """Save a competitor's weekly snapshot as JSON."""
    wdir = week_dir(week)
    wdir.mkdir(parents=True, exist_ok=True)
    filepath = wdir / f"{username}.json"
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return filepath


def load_snapshot(username: str, week: str) -> dict | None:
    """Load a competitor's snapshot for a given week."""
    filepath = week_dir(week) / f"{username}.json"
    if not filepath.exists():
        return None
    with open(filepath) as f:
        return json.load(f)


def list_weeks() -> list[str]:
    """List all stored week labels, sorted chronologically."""
    if not DATA_DIR.exists():
        return []
    weeks = [d.name for d in DATA_DIR.iterdir() if d.is_dir() and d.name.startswith("20")]
    return sorted(weeks)


def resolve_week_range(spec: str) -> list[str]:
    """Resolve a week range spec into a list of week labels.

    Supported formats:
      - "2026-W09:2026-W12"  explicit range
      - "9-12" or "9:12"     week numbers in current year
      - "latest-4"           last 4 collected weeks
      - "all"                all collected weeks
    """
    all_weeks = list_weeks()
    if not all_weeks:
        return []

    spec = spec.strip()

    if spec == "all":
        return all_weeks

    if spec.startswith("latest"):
        n = int(spec.split("-")[1]) if "-" in spec else 4
        return all_weeks[-n:]

    # Explicit ISO week range: "2026-W09:2026-W12"
    if "W" in spec:
        sep = ":" if ":" in spec else "-" if spec.count("-") > 2 else ":"
        parts = spec.split(sep) if sep in spec else [spec]
        if len(parts) == 2:
            start, end = parts
            return [w for w in all_weeks if start <= w <= end]
        return [w for w in all_weeks if w == spec]

    # Short week numbers: "9-12" or "9:12"
    sep = ":" if ":" in spec else "-"
    parts = spec.split(sep)
    if len(parts) == 2:
        year = date.today().isocalendar()[0]
        start_w = int(parts[0])
        end_w = int(parts[1])
        start = f"{year}-W{start_w:02d}"
        end = f"{year}-W{end_w:02d}"
        return [w for w in all_weeks if start <= w <= end]

    return all_weeks


def thumbnails_dir(week: str | None = None) -> Path:
    """Return the thumbnails directory for a given week."""
    tdir = week_dir(week) / "thumbnails"
    tdir.mkdir(parents=True, exist_ok=True)
    return tdir


def cleanup_old_weeks(keep: int = 52) -> None:
    """Remove weeks older than the most recent `keep` weeks."""
    all_weeks = list_weeks()
    if len(all_weeks) <= keep:
        return
    to_remove = all_weeks[:-keep]
    for week in to_remove:
        shutil.rmtree(week_dir(week), ignore_errors=True)
