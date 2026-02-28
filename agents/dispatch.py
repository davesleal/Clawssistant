"""Agent dispatch — routes work to the right agent via GitHub Actions workflows.

The orchestrator calls dispatch functions to trigger agent workflows. Each
dispatch encodes the trigger context into workflow inputs so the receiving
agent can reconstruct the full picture.
"""

from __future__ import annotations

import logging
from typing import Any

from agents.config import AgentRole
from agents.github_ops import GitHubOps

logger = logging.getLogger("clawssistant.agents.dispatch")

# Mapping from agent role to workflow filename
WORKFLOW_MAP: dict[AgentRole, str] = {
    AgentRole.TRIAGE: "agent-triage.yml",
    AgentRole.ENGINEER: "agent-develop.yml",
    AgentRole.SR_ENGINEER: "agent-review.yml",
    AgentRole.SECURITY: "agent-security.yml",
    AgentRole.INFOSEC: "agent-security.yml",  # same workflow, different input
    AgentRole.QA: "agent-qa.yml",
    AgentRole.WILDCARD: "agent-wildcard.yml",
    AgentRole.BLOG: "agent-blog.yml",
    AgentRole.PM: "agent-triage.yml",  # PM participates in triage flow
}


def dispatch_agent(
    github: GitHubOps,
    role: AgentRole,
    trigger: dict[str, Any],
    ref: str = "main",
) -> dict[str, Any]:
    """Dispatch an agent by triggering its GitHub Actions workflow.

    Args:
        github: GitHub operations client.
        role: Which agent role to dispatch.
        trigger: Context dict with at minimum {"issue_number": int} or similar.
        ref: Git ref to run the workflow against.

    Returns:
        Result from the workflow dispatch API call.
    """
    workflow = WORKFLOW_MAP.get(role)
    if not workflow:
        return {"error": f"No workflow mapped for role: {role.value}"}

    # Flatten trigger dict to string values (workflow inputs must be strings)
    inputs = {k: str(v) for k, v in trigger.items()}
    inputs["agent_role"] = role.value

    logger.info("Dispatching %s agent via %s with inputs: %s", role.value, workflow, inputs)
    return github.dispatch_workflow(workflow, ref=ref, inputs=inputs)


def dispatch_engineer_for_ticket(
    github: GitHubOps,
    issue_number: int,
    ref: str = "main",
) -> dict[str, Any]:
    """Dispatch an engineer agent to work on a specific ticket."""
    return dispatch_agent(
        github,
        AgentRole.ENGINEER,
        {"issue_number": issue_number, "action": "develop"},
        ref=ref,
    )


def dispatch_review(
    github: GitHubOps,
    pr_number: int,
    issue_number: int,
    ref: str = "main",
) -> dict[str, Any]:
    """Dispatch a senior engineer review for a PR."""
    return dispatch_agent(
        github,
        AgentRole.SR_ENGINEER,
        {"pr_number": pr_number, "issue_number": issue_number, "action": "review"},
        ref=ref,
    )


def dispatch_security_review(
    github: GitHubOps,
    pr_number: int,
    issue_number: int,
    ref: str = "main",
) -> dict[str, Any]:
    """Dispatch both security and infosec agents for pair review."""
    # Security engineer
    result_sec = dispatch_agent(
        github,
        AgentRole.SECURITY,
        {
            "pr_number": pr_number,
            "issue_number": issue_number,
            "action": "security-review",
            "agent_role": "security",
        },
        ref=ref,
    )
    # InfoSec agent
    result_infosec = dispatch_agent(
        github,
        AgentRole.INFOSEC,
        {
            "pr_number": pr_number,
            "issue_number": issue_number,
            "action": "security-review",
            "agent_role": "infosec",
        },
        ref=ref,
    )
    return {"security": result_sec, "infosec": result_infosec}


def dispatch_qa(
    github: GitHubOps,
    pr_number: int,
    issue_number: int,
    ref: str = "main",
) -> dict[str, Any]:
    """Dispatch QA agent after security approval."""
    return dispatch_agent(
        github,
        AgentRole.QA,
        {"pr_number": pr_number, "issue_number": issue_number, "action": "qa"},
        ref=ref,
    )


def dispatch_deploy(
    github: GitHubOps,
    pr_number: int,
    issue_number: int,
    ref: str = "main",
) -> dict[str, Any]:
    """Dispatch deployment after QA passes."""
    return github.dispatch_workflow(
        "agent-deploy.yml",
        ref=ref,
        inputs={
            "pr_number": str(pr_number),
            "issue_number": str(issue_number),
            "action": "deploy",
        },
    )


def dispatch_wildcard_scan(github: GitHubOps, ref: str = "main") -> dict[str, Any]:
    """Dispatch the wildcard codebase scanner."""
    return dispatch_agent(
        github,
        AgentRole.WILDCARD,
        {"action": "scan"},
        ref=ref,
    )


def dispatch_blog_post(
    github: GitHubOps,
    topic: str,
    context: str = "",
    ref: str = "main",
) -> dict[str, Any]:
    """Dispatch the blog writer agent."""
    return dispatch_agent(
        github,
        AgentRole.BLOG,
        {"action": "write", "topic": topic, "context": context},
        ref=ref,
    )


def escalate_block(
    github: GitHubOps,
    issue_number: int,
    blocked_agent: str,
    block_reason: str,
    ref: str = "main",
) -> dict[str, Any]:
    """Escalate a blocked engineer to the orchestrator for help."""
    return github.dispatch_workflow(
        "agent-orchestrator.yml",
        ref=ref,
        inputs={
            "action": "escalate",
            "issue_number": str(issue_number),
            "blocked_agent": blocked_agent,
            "block_reason": block_reason,
        },
    )
