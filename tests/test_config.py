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


class TestLoadConfig:
    def test_valid_config(self, tmp_path):
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
        assert config.months_back == 3
        assert config.output_dir == Path("./results")

    def test_defaults(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "competitors": [{"username": "nike"}],
        }))
        config = load_config(config_file)
        assert config.months_back == 6
        assert config.output_dir == Path("./output")

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
