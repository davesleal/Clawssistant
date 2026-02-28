"""Agent configuration — role definitions, capabilities, and constraints."""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class AgentRole(Enum):
    ORCHESTRATOR = "orchestrator"
    PM = "pm"
    TRIAGE = "triage"
    RESEARCHER = "researcher"
    DATA_SCIENTIST = "data-scientist"
    ENGINEER = "engineer"
    SR_ENGINEER = "sr-engineer"
    SECURITY = "security"
    INFOSEC = "infosec"
    QA = "qa"
    WILDCARD = "wildcard"
    BLOG = "blog"


# ---------------------------------------------------------------------------
# Agent capability declarations
# ---------------------------------------------------------------------------

AGENT_CAPABILITIES: dict[AgentRole, dict[str, Any]] = {
    AgentRole.ORCHESTRATOR: {
        "model": "claude-sonnet-4-6",
        "max_tokens": 8192,
        "can_dispatch": True,
        "can_create_issues": True,
        "can_manage_board": True,
        "can_close_issues": True,
        "response_delay_minutes": 15,
        "description": (
            "Root coordinator. Dispatches agents, manages board and timeline, "
            "ensures documentation and wiki are current. All agents report here."
        ),
    },
    AgentRole.PM: {
        "model": "claude-sonnet-4-6",
        "max_tokens": 8192,
        "can_dispatch": True,
        "can_create_issues": True,
        "can_manage_board": True,
        "can_write_blog": True,
        "can_close_issues": True,
        "response_delay_minutes": 15,
        "description": (
            "Product manager. Reviews issues and discussions, collaborates with users "
            "via tagging, writes epics/features/user stories, manages board and "
            "timeline, publishes blog posts."
        ),
    },
    AgentRole.TRIAGE: {
        "model": "claude-sonnet-4-6",
        "max_tokens": 4096,
        "can_label_issues": True,
        "can_create_issues": True,
        "response_delay_minutes": 15,
        "description": (
            "Triage coordinator. Evaluates new issues/discussions for feasibility, "
            "scope, and priority by combining researcher, data scientist, and "
            "engineer perspectives."
        ),
    },
    AgentRole.RESEARCHER: {
        "model": "claude-sonnet-4-6",
        "max_tokens": 4096,
        "response_delay_minutes": 20,
        "description": (
            "Senior user researcher. Evaluates feature requests from the user "
            "perspective — usability, user need, market fit, competitive analysis."
        ),
    },
    AgentRole.DATA_SCIENTIST: {
        "model": "claude-sonnet-4-6",
        "max_tokens": 4096,
        "response_delay_minutes": 20,
        "description": (
            "Data scientist. Assesses scope, estimates effort, analyzes priority "
            "using project data, issue velocity, and roadmap alignment."
        ),
    },
    AgentRole.ENGINEER: {
        "model": "claude-sonnet-4-6",
        "max_tokens": 8192,
        "can_create_branches": True,
        "can_write_code": True,
        "can_create_prs": True,
        "response_delay_minutes": 15,
        "persist_until_done": True,
        "description": (
            "Development engineer. Writes code, creates PRs, persists on a ticket "
            "until it is deployed or archived. Engages other engineers when blocked."
        ),
    },
    AgentRole.SR_ENGINEER: {
        "model": "claude-sonnet-4-6",
        "max_tokens": 8192,
        "can_review_prs": True,
        "can_approve_prs": True,
        "can_request_changes": True,
        "response_delay_minutes": 15,
        "description": (
            "Senior software engineer. Reviews PRs for code quality, architecture, "
            "test coverage, and adherence to project standards. Can split large "
            "reviews across multiple engineer agents."
        ),
    },
    AgentRole.SECURITY: {
        "model": "claude-sonnet-4-6",
        "max_tokens": 4096,
        "can_review_prs": True,
        "can_block_deploy": True,
        "response_delay_minutes": 15,
        "description": (
            "Security engineer. Scans code for vulnerabilities (OWASP top 10, "
            "dependency issues, auth flaws). Must approve before deployment."
        ),
    },
    AgentRole.INFOSEC: {
        "model": "claude-sonnet-4-6",
        "max_tokens": 4096,
        "can_review_prs": True,
        "can_block_deploy": True,
        "response_delay_minutes": 15,
        "description": (
            "Information security agent. Reviews from a threat modeling and "
            "compliance perspective. Pair-programs with security engineer on every "
            "review. Both must approve for deployment."
        ),
    },
    AgentRole.QA: {
        "model": "claude-sonnet-4-6",
        "max_tokens": 4096,
        "can_run_tests": True,
        "can_create_issues": True,
        "response_delay_minutes": 15,
        "description": (
            "QA engineer. Validates deployed changes, runs test suites, performs "
            "exploratory testing, and files regression bugs."
        ),
    },
    AgentRole.WILDCARD: {
        "model": "claude-sonnet-4-6",
        "max_tokens": 8192,
        "can_create_issues": True,
        "can_scan_codebase": True,
        "response_delay_minutes": 30,
        "description": (
            "Wildcard auditor. Periodically scans the entire codebase for tech debt, "
            "security issues, dead code, architectural drift, and improvement "
            "opportunities. Files issues for findings."
        ),
    },
    AgentRole.BLOG: {
        "model": "claude-sonnet-4-6",
        "max_tokens": 4096,
        "can_write_blog": True,
        "can_commit_files": True,
        "response_delay_minutes": 30,
        "description": (
            "Blog writer. Drafts and publishes blog posts about releases, roadmap "
            "updates, and project milestones to the GitHub Pages site."
        ),
    },
}


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

_config_cache: dict[str, Any] | None = None


def _load_agents_yaml() -> dict[str, Any]:
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    config_path = Path(__file__).parent / "agents.yaml"
    if config_path.exists():
        with open(config_path) as f:
            _config_cache = yaml.safe_load(f) or {}
    else:
        _config_cache = {}
    return _config_cache


def get_agent_config(role: AgentRole) -> dict[str, Any]:
    """Get the merged config for an agent role (defaults + YAML overrides)."""
    defaults = AGENT_CAPABILITIES.get(role, {})
    yaml_config = _load_agents_yaml().get("agents", {}).get(role.value, {})

    merged = {**defaults, **yaml_config}

    # Load system prompt from YAML or use empty
    if "system_prompt" not in merged:
        merged["system_prompt"] = ""

    return merged


def get_response_delay(role: AgentRole) -> int:
    """Get the response delay in minutes for an agent role."""
    config = get_agent_config(role)
    return config.get("response_delay_minutes", 15)
