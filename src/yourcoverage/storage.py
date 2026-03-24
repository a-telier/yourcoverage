"""Backward-compatible helpers — delegates to database.py."""

from datetime import date


def week_label(dt: date | None = None) -> str:
    """Return ISO week label like '2026-W12'."""
    if dt is None:
        dt = date.today()
    year, week, _ = dt.isocalendar()
    return f"{year}-W{week:02d}"


def screenshots_dir_for_week(base_dir, week: str):
    """Return the screenshots directory for a given week."""
    from pathlib import Path
    d = Path(base_dir) / "screenshots" / week
    d.mkdir(parents=True, exist_ok=True)
    return d
