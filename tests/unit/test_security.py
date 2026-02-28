"""Tests for security invariants.

These tests verify that security-critical defaults and behaviors are correct.
They act as guardrails — if someone accidentally weakens a default, these fail.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).parents[2]


class TestSecurityDefaults:
    """Security defaults must not regress."""

    @pytest.fixture
    def example_config(self) -> dict:
        config_path = PROJECT_ROOT / "config.example.yaml"
        if not config_path.exists():
            pytest.skip("config.example.yaml not found")
        with open(config_path) as f:
            return yaml.safe_load(f)

    def test_api_auth_enabled(self, example_config: dict) -> None:
        """API authentication must be enabled by default."""
        assert example_config["api"]["auth"]["enabled"] is True

    def test_api_binds_localhost(self, example_config: dict) -> None:
        """API must bind 127.0.0.1, not 0.0.0.0."""
        assert example_config["api"]["host"] == "127.0.0.1"

    def test_rate_limiting_configured(self, example_config: dict) -> None:
        """Rate limiting must be set."""
        assert example_config["api"]["auth"]["rate_limit"] > 0

    def test_audit_logging_enabled(self, example_config: dict) -> None:
        """Audit logging must be on by default."""
        assert example_config["security"]["audit_log"]["enabled"] is True

    def test_medium_risk_confirmation(self, example_config: dict) -> None:
        """Medium-risk voice actions must require confirmation."""
        assert example_config["security"]["voice"]["confirm_medium_risk"] is True

    def test_high_risk_pin(self, example_config: dict) -> None:
        """High-risk actions must require PIN."""
        assert example_config["security"]["voice"]["pin_for_high_risk"] is True

    def test_skill_manifest_required(self, example_config: dict) -> None:
        """Skills must declare a manifest."""
        assert example_config["skills"]["require_manifest"] is True

    def test_developer_skills_disabled(self, example_config: dict) -> None:
        """Developer skills (shell, code) must NOT be enabled by default."""
        enabled = example_config["skills"]["enabled"]
        assert "dev.code" not in enabled
        assert "dev.shell" not in enabled


class TestSecurityFilesExist:
    """Required security files must exist in the repo."""

    def test_security_md_exists(self) -> None:
        assert (PROJECT_ROOT / "SECURITY.md").exists()

    def test_gitignore_excludes_config(self) -> None:
        gitignore = (PROJECT_ROOT / ".gitignore").read_text()
        assert "config.yaml" in gitignore

    def test_gitignore_excludes_env(self) -> None:
        gitignore = (PROJECT_ROOT / ".gitignore").read_text()
        assert ".env" in gitignore

    def test_gitignore_excludes_secrets(self) -> None:
        gitignore = (PROJECT_ROOT / ".gitignore").read_text()
        assert "secrets.yaml" in gitignore

    def test_gitignore_excludes_databases(self) -> None:
        gitignore = (PROJECT_ROOT / ".gitignore").read_text()
        assert "*.db" in gitignore or "*.sqlite" in gitignore


class TestInputValidation:
    """Input validation helpers for security-critical paths."""

    @pytest.mark.parametrize(
        "path,safe",
        [
            ("skills/my_skill.py", True),
            ("skills/../../../etc/passwd", False),
            ("/etc/shadow", False),
            ("skills/subfolder/skill.py", True),
            ("skills/skill.py\x00.txt", False),  # null byte injection
        ],
    )
    def test_path_traversal_detection(self, path: str, safe: bool) -> None:
        """Paths with traversal or injection attempts should be detected."""
        from pathlib import PurePosixPath

        normalized = str(PurePosixPath(path))
        is_safe = (
            not normalized.startswith("/")
            and ".." not in normalized
            and "\x00" not in path
        )
        assert is_safe == safe

    @pytest.mark.parametrize(
        "entity_id,safe",
        [
            ("light.living_room", True),
            ("light.living_room; DROP TABLE", False),
            ("light.living_room' OR '1'='1", False),
            ("climate.thermostat", True),
        ],
    )
    def test_entity_id_injection(self, entity_id: str, safe: bool) -> None:
        """Entity IDs with SQL/command injection should be rejected."""
        import re

        # Entity IDs should only contain alphanumeric, underscore, dot
        is_safe = bool(re.match(r"^[a-z_]+\.[a-z0-9_]+$", entity_id))
        assert is_safe == safe
