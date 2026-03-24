"""Tests for config loading and URL parsing."""

import pytest
import yaml
from pathlib import Path

from yourcoverage.config import load_config, _extract_username


class TestExtractUsername:
    def test_plain_username(self):
        assert _extract_username("nike") == "nike"

    def test_username_with_at(self):
        assert _extract_username("@nike") == "nike"

    def test_full_url(self):
        assert _extract_username("https://www.instagram.com/nike/") == "nike"

    def test_url_without_trailing_slash(self):
        assert _extract_username("https://instagram.com/nike") == "nike"

    def test_url_with_query_params(self):
        assert _extract_username("https://www.instagram.com/nike?hl=en") == "nike"

    def test_uppercase_normalized(self):
        assert _extract_username("Nike") == "nike"

    def test_url_with_igsh_param(self):
        assert _extract_username(
            "https://www.instagram.com/zarahome?igsh=bHFuZG9pcjR2MjN5"
        ) == "zarahome"


class TestLoadConfig:
    def test_legacy_config(self, tmp_path):
        """Legacy format with username-only entries still works."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "competitors": [
                {"username": "nike"},
                {"username": "https://www.instagram.com/adidas/"},
            ],
            "months_back": 3,
            "output_dir": "./results",
        }))
        config = load_config(config_file)
        assert config.usernames == ["nike", "adidas"]
        assert len(config.competitors) == 2
        assert config.competitors[0].name == "@nike"

    def test_new_format_config(self, tmp_path):
        """New format with name, instagram, website, color."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "competitors": [
                {
                    "name": "Zara Home",
                    "instagram": "https://www.instagram.com/zarahome",
                    "website": "https://www.zarahome.com/se/",
                    "color": "#c4a35a",
                },
                {
                    "name": "IKEA",
                    "instagram": "https://www.instagram.com/ikea",
                    "website": "https://www.ikea.com/se/sv/",
                    "color": "#0058a3",
                },
            ],
            "collection": {
                "weeks_to_keep": 52,
                "posts_per_profile": 20,
            },
            "report": {
                "output_dir": "./docs",
                "default_weeks": "latest-4",
            },
        }))
        config = load_config(config_file)
        assert len(config.competitors) == 2
        assert config.competitors[0].name == "Zara Home"
        assert config.competitors[0].instagram_username == "zarahome"
        assert config.competitors[0].website_url == "https://www.zarahome.com/se/"
        assert config.competitors[0].color == "#c4a35a"
        assert config.competitors[1].name == "IKEA"
        assert config.usernames == ["zarahome", "ikea"]
        assert config.collection.weeks_to_keep == 52
        assert config.report.output_dir == Path("./docs")

    def test_defaults(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "competitors": [{"username": "nike"}],
        }))
        config = load_config(config_file)
        assert config.collection.weeks_to_keep == 52
        assert config.collection.posts_per_profile == 20
        assert config.report.default_weeks == "latest-4"

    def test_missing_file(self):
        with pytest.raises(ValueError, match="not found"):
            load_config(Path("/nonexistent.yaml"))

    def test_empty_competitors(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"competitors": []}))
        with pytest.raises(ValueError, match="empty"):
            load_config(config_file)

    def test_missing_competitors_key(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"other": "data"}))
        with pytest.raises(ValueError, match="competitors"):
            load_config(config_file)
