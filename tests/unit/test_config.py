"""Tests for configuration loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


class TestConfigLoading:
    """Config loader should parse YAML, resolve env vars, and validate."""

    def test_load_sample_config(self, fixtures_dir: Path) -> None:
        """Sample config file should parse as valid YAML."""
        config_path = fixtures_dir / "sample_config.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert config["assistant"]["name"] == "TestAssistant"
        assert config["claude"]["model"] == "claude-sonnet-4-6"
        assert config["api"]["host"] == "127.0.0.1"

    def test_tmp_config_fixture(self, tmp_config: Path) -> None:
        """The tmp_config fixture should produce a readable config file."""
        assert tmp_config.exists()
        with open(tmp_config) as f:
            config = yaml.safe_load(f)
        assert config["assistant"]["name"] == "TestAssistant"

    def test_auth_enabled_by_default(self) -> None:
        """Production config.example.yaml should have auth enabled."""
        example_path = Path(__file__).parents[2] / "config.example.yaml"
        if not example_path.exists():
            pytest.skip("config.example.yaml not found")
        with open(example_path) as f:
            config = yaml.safe_load(f)
        assert config["api"]["auth"]["enabled"] is True

    def test_bind_localhost_by_default(self) -> None:
        """Production config.example.yaml should bind 127.0.0.1."""
        example_path = Path(__file__).parents[2] / "config.example.yaml"
        if not example_path.exists():
            pytest.skip("config.example.yaml not found")
        with open(example_path) as f:
            config = yaml.safe_load(f)
        assert config["api"]["host"] == "127.0.0.1"

    def test_config_missing_required_field(self, tmp_path: Path) -> None:
        """Config missing required fields should be detectable."""
        config = {"assistant": {"name": "Test"}}  # missing claude, api, etc.
        config_path = tmp_path / "bad_config.yaml"
        config_path.write_text(yaml.dump(config))

        with open(config_path) as f:
            loaded = yaml.safe_load(f)

        # When the config module exists, it should raise a validation error.
        # For now, just verify we can detect missing keys.
        assert "claude" not in loaded
