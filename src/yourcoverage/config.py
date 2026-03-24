"""Load and validate competitor configuration."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

_DEFAULT_COLORS = [
    "#c4a35a", "#0058a3", "#d4a574", "#e74c3c", "#2ecc71",
    "#9b59b6", "#f39c12", "#1abc9c", "#e67e22", "#3498db",
]


@dataclass
class Competitor:
    name: str
    slug: str
    website_url: str
    color: str


@dataclass
class CollectionSettings:
    weeks_to_keep: int = 52
    screenshot: bool = True
    timeout: int = 30000


@dataclass
class ReportSettings:
    output_dir: Path = field(default_factory=lambda: Path("./docs"))
    default_weeks: str = "latest-4"


@dataclass
class Config:
    competitors: list[Competitor]
    collection: CollectionSettings
    report: ReportSettings
    database: Path = field(default_factory=lambda: Path("./data/yourcoverage.db"))


def load_config(path: Path) -> Config:
    """Load competitor config from a YAML file."""
    if not path.exists():
        raise ValueError(f"Config file not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "competitors" not in data:
        raise ValueError("Config must contain a 'competitors' list")

    competitors_raw = data["competitors"]
    if not competitors_raw:
        raise ValueError("Competitors list is empty")

    competitors = []
    for i, entry in enumerate(competitors_raw):
        if not isinstance(entry, dict):
            raise ValueError(f"Invalid competitor entry: {entry}")

        name = entry.get("name")
        slug = entry.get("slug")
        website = entry.get("website", "")

        if not name or not slug:
            raise ValueError(f"Competitor must have 'name' and 'slug': {entry}")
        if not website:
            raise ValueError(f"Competitor '{name}' must have a 'website' URL")

        competitors.append(Competitor(
            name=name,
            slug=slug,
            website_url=website,
            color=entry.get("color", _DEFAULT_COLORS[i % len(_DEFAULT_COLORS)]),
        ))

    coll_data = data.get("collection", {})
    collection = CollectionSettings(
        weeks_to_keep=coll_data.get("weeks_to_keep", 52),
        screenshot=coll_data.get("screenshot", True),
        timeout=coll_data.get("timeout", 30000),
    )

    rep_data = data.get("report", {})
    report = ReportSettings(
        output_dir=Path(rep_data.get("output_dir", "./docs")),
        default_weeks=rep_data.get("default_weeks", "latest-4"),
    )

    db_path = Path(data.get("database", "./data/yourcoverage.db"))

    return Config(
        competitors=competitors,
        collection=collection,
        report=report,
        database=db_path,
    )
