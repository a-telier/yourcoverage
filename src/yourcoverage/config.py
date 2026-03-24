"""Load and validate competitor configuration."""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_INSTAGRAM_URL_PATTERN = re.compile(r"instagram\.com/([^/?#]+)")

# Default colors for competitors without explicit color
_DEFAULT_COLORS = [
    "#c4a35a", "#0058a3", "#d4a574", "#e74c3c", "#2ecc71",
    "#9b59b6", "#f39c12", "#1abc9c", "#e67e22", "#3498db",
]


@dataclass
class Competitor:
    name: str
    instagram_username: str
    instagram_url: str
    website_url: str
    color: str


@dataclass
class CollectionSettings:
    weeks_to_keep: int = 52
    posts_per_profile: int = 20
    download_thumbnails: bool = True
    website_screenshot: bool = True


@dataclass
class ReportSettings:
    output_dir: Path = field(default_factory=lambda: Path("./docs"))
    default_weeks: str = "latest-4"


@dataclass
class Config:
    competitors: list[Competitor]
    collection: CollectionSettings
    report: ReportSettings

    # Legacy compatibility
    @property
    def usernames(self) -> list[str]:
        return [c.instagram_username for c in self.competitors]


def _extract_username(url: str) -> str:
    """Extract Instagram username from a URL or plain username."""
    url = url.strip().rstrip("/")
    match = _INSTAGRAM_URL_PATTERN.search(url)
    if match:
        return match.group(1).lower()
    return url.lstrip("@").lower()


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
        if isinstance(entry, str):
            # Legacy format: just a username
            username = _extract_username(entry)
            competitors.append(Competitor(
                name=f"@{username}",
                instagram_username=username,
                instagram_url=f"https://www.instagram.com/{username}/",
                website_url="",
                color=_DEFAULT_COLORS[i % len(_DEFAULT_COLORS)],
            ))
        elif isinstance(entry, dict):
            if "username" in entry and "instagram" not in entry:
                # Legacy format: {username: "nike"}
                username = _extract_username(entry["username"])
                competitors.append(Competitor(
                    name=entry.get("name", f"@{username}"),
                    instagram_username=username,
                    instagram_url=f"https://www.instagram.com/{username}/",
                    website_url=entry.get("website", ""),
                    color=entry.get("color", _DEFAULT_COLORS[i % len(_DEFAULT_COLORS)]),
                ))
            elif "instagram" in entry:
                # New format
                username = _extract_username(entry["instagram"])
                competitors.append(Competitor(
                    name=entry.get("name", f"@{username}"),
                    instagram_username=username,
                    instagram_url=entry["instagram"],
                    website_url=entry.get("website", ""),
                    color=entry.get("color", _DEFAULT_COLORS[i % len(_DEFAULT_COLORS)]),
                ))
            else:
                raise ValueError(f"Invalid competitor entry: {entry}")
        else:
            raise ValueError(f"Invalid competitor entry: {entry}")

    if not competitors:
        raise ValueError("No valid competitors found")

    # Collection settings
    coll_data = data.get("collection", {})
    collection = CollectionSettings(
        weeks_to_keep=coll_data.get("weeks_to_keep", 52),
        posts_per_profile=coll_data.get("posts_per_profile", 20),
        download_thumbnails=coll_data.get("download_thumbnails", True),
        website_screenshot=coll_data.get("website_screenshot", True),
    )

    # Report settings
    rep_data = data.get("report", {})
    report = ReportSettings(
        output_dir=Path(rep_data.get("output_dir", "./docs")),
        default_weeks=rep_data.get("default_weeks", "latest-4"),
    )

    return Config(competitors=competitors, collection=collection, report=report)
