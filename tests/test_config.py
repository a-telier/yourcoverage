"""Tests for config loading."""

import pytest
import yaml
from pathlib import Path

from yourcoverage.config import load_config


class TestLoadConfig:
    def test_basic_config(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "competitors": [
                {
                    "name": "Zara Home",
                    "slug": "zarahome",
                    "website": "https://www.zarahome.com/se/",
                    "color": "#c4a35a",
                },
                {
                    "name": "IKEA",
                    "slug": "ikea",
                    "website": "https://www.ikea.com/se/sv/",
                },
            ],
            "database": "./data/test.db",
        }))
        config = load_config(config_file)
        assert len(config.competitors) == 2
        assert config.competitors[0].name == "Zara Home"
        assert config.competitors[0].slug == "zarahome"
        assert config.competitors[0].website_url == "https://www.zarahome.com/se/"
        assert config.competitors[0].color == "#c4a35a"
        assert config.competitors[1].color.startswith("#")  # default assigned
        assert config.database == Path("./data/test.db")

    def test_defaults(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "competitors": [
                {"name": "Test", "slug": "test", "website": "https://test.com"},
            ],
        }))
        config = load_config(config_file)
        assert config.collection.weeks_to_keep == 52
        assert config.collection.screenshot is True
        assert config.collection.timeout == 30000
        assert config.report.default_weeks == "latest-4"

    def test_missing_website_raises(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "competitors": [{"name": "No Site", "slug": "nosite"}],
        }))
        with pytest.raises(ValueError, match="website"):
            load_config(config_file)

    def test_missing_slug_raises(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "competitors": [{"name": "No Slug", "website": "https://x.com"}],
        }))
        with pytest.raises(ValueError, match="slug"):
            load_config(config_file)

    def test_missing_file(self):
        with pytest.raises(ValueError, match="not found"):
            load_config(Path("/nonexistent.yaml"))

    def test_empty_competitors(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"competitors": []}))
        with pytest.raises(ValueError, match="empty"):
            load_config(config_file)
