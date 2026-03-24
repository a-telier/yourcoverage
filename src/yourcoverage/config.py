"""Load and validate competitor configuration."""

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

_INSTAGRAM_URL_PATTERN = re.compile(r"instagram\.com/([^/?#]+)")


@dataclass
class Config:
    usernames: list[str]
    months_back: int
    output_dir: Path


def _extract_username(value: str) -> str:
    """Extract Instagram username from a URL or plain username."""
    value = value.strip().rstrip("/")
    match = _INSTAGRAM_URL_PATTERN.search(value)
    if match:
        return match.group(1).lower()
    # Treat as plain username, strip leading @
    return value.lstrip("@").lower()


def load_config(path: Path) -> Config:
    """Load competitor config from a YAML file."""
    if not path.exists():
        raise ValueError(f"Config file not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "competitors" not in data:
        raise ValueError("Config must contain a 'competitors' list")

    competitors = data["competitors"]
    if not competitors:
        raise ValueError("Competitors list is empty")

    usernames = []
    for entry in competitors:
        if isinstance(entry, str):
            usernames.append(_extract_username(entry))
        elif isinstance(entry, dict) and "username" in entry:
            usernames.append(_extract_username(entry["username"]))
        else:
            raise ValueError(f"Invalid competitor entry: {entry}")

    if not usernames:
        raise ValueError("No valid usernames found")

    return Config(
        usernames=usernames,
        months_back=data.get("months_back", 6),
        output_dir=Path(data.get("output_dir", "./output")),
    )
