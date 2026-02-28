"""Unified entry point for running any agent from the command line.

Usage:
    python -m agents.scripts.run_agent --role orchestrator --action cycle
    python -m agents.scripts.run_agent --role triage --issue-number 42
    python -m agents.scripts.run_agent --role engineer --action develop --issue-number 42
    python -m agents.scripts.run_agent --role security --extra "pr_number=7" --extra "issue_number=42"
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("clawssistant.agents")


# Agent class registry — maps role names to their implementation classes
AGENT_REGISTRY: dict[str, type] = {}


def _register_agents() -> None:
    """Lazily import and register all agent classes."""
    from agents.roles.orchestrator import OrchestratorAgent
    from agents.roles.pm import PMAgent
    from agents.roles.triage import TriageAgent
    from agents.roles.triad import TriadSquadAgent
    from agents.roles.reviewer import ReviewerAgent
    from agents.roles.security import SecurityAgent, InfoSecAgent
    from agents.roles.qa import QAAgent
    from agents.roles.wildcard import WildcardAgent
    from agents.roles.blog import BlogAgent

    AGENT_REGISTRY.update({
        "orchestrator": OrchestratorAgent,
        "pm": PMAgent,
        "triage": TriageAgent,
        "engineer": TriadSquadAgent,  # Engineer role uses the triad squad
        "sr-engineer": ReviewerAgent,
        "security": SecurityAgent,
        "infosec": InfoSecAgent,
        "qa": QAAgent,
        "wildcard": WildcardAgent,
        "blog": BlogAgent,
    })


def parse_extras(extras: list[str]) -> dict[str, str]:
    """Parse --extra key=value pairs into a dict."""
    result: dict[str, str] = {}
    for item in extras:
        if "=" in item:
            key, _, value = item.partition("=")
            result[key.strip()] = value.strip()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Clawssistant agent")
    parser.add_argument("--role", required=True, help="Agent role to run")
    parser.add_argument("--action", default="", help="Action to perform")
    parser.add_argument("--issue-number", default="0", help="Issue number")
    parser.add_argument("--extra", action="append", default=[], help="Extra params (key=value)")

    args = parser.parse_args()

    _register_agents()

    agent_class = AGENT_REGISTRY.get(args.role)
    if not agent_class:
        logger.error("Unknown agent role: %s. Available: %s", args.role, list(AGENT_REGISTRY.keys()))
        sys.exit(1)

    # Build trigger dict
    trigger: dict[str, Any] = {
        "action": args.action,
        "issue_number": args.issue_number,
    }
    trigger.update(parse_extras(args.extra))

    logger.info("Starting %s agent with trigger: %s", args.role, trigger)

    try:
        agent = agent_class()
        agent.run(trigger)
        logger.info("%s agent completed successfully", args.role)
    except Exception:
        logger.exception("Agent %s failed", args.role)
        sys.exit(1)


if __name__ == "__main__":
    main()
