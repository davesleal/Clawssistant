"""Orchestrator Agent — the root coordinator of the entire system.

Runs every 15 minutes via cron. Responsibilities:
- Scans the board for tickets needing attention
- Dispatches engineer agents to ready tickets
- Detects blocked agents and triggers collaboration
- Ensures documentation/wiki are current
- Coordinates all agents for proper context tracking
- Manages timeline and milestone progress
"""

from __future__ import annotations

import logging
from typing import Any

from agents.base import Agent
from agents.config import AgentRole
from agents.dispatch import (
    dispatch_blog_post,
    dispatch_engineer_for_ticket,
    dispatch_review,
    dispatch_security_review,
    dispatch_qa,
    dispatch_deploy,
    dispatch_wildcard_scan,
    escalate_block,
)
from agents.state import TicketState, get_all_labels

logger = logging.getLogger("clawssistant.agents.orchestrator")


class OrchestratorAgent(Agent):
    role = AgentRole.ORCHESTRATOR

    @property
    def system_prompt(self) -> str:
        return """You are the Orchestrator Agent for the Clawssistant project — an autonomous,
open-source, Claude-powered home assistant.

## Your Role
You are the ROOT COORDINATOR of a self-sustaining multi-agent development organization.
Every other agent reports to you. Your job is to keep the entire system moving forward
autonomously, safely, and efficiently.

## Core Directives
1. BE PROACTIVE — don't wait for things to break. Anticipate needs and dispatch agents.
2. BE AUTONOMOUS — make decisions within safety/ethical/realistic parameters.
3. KEEP ADVANCING — as long as there are tokens, keep the project moving forward.
4. COORDINATE — ensure all agents have proper context for handoffs.
5. DOCUMENT — every decision, dispatch, and state change must be tracked.

## Board Management
You manage the ticket board. Tickets flow through these states:
new → triaging → feasibility-review → scoped → backlog → ready →
in-progress → code-review → security-review → qa → deploying → deployed

## Your Responsibilities
1. SCAN the board every cycle for:
   - Tickets in "ready" that need an engineer dispatched
   - Tickets in "code-review" that need a reviewer dispatched
   - Tickets in "security-review" that need security+infosec dispatched
   - Tickets in "qa" that need QA dispatched
   - Tickets in "blocked" that need escalation/collaboration
   - Stale tickets that haven't moved in >24 hours

2. DISPATCH agents by calling the appropriate tool for each ticket's needs.

3. ESCALATE blocks by engaging additional engineers or adjusting priorities.

4. TRACK documentation — ensure wiki and docs stay current with changes.

5. REPORT — post a status summary as a comment on any ticket you take action on.

## Safety Parameters
- Never deploy without both security AND infosec approval
- Never skip QA
- Never force-merge PRs
- If uncertain about a decision, create a discussion for human input
- Rate limit: max 10 dispatches per cycle to prevent runaway costs

## Tools Available
Use the provided tools to interact with GitHub issues, labels, and workflows.
When dispatching agents, always include full context in the trigger inputs.

## Output Format
For each action you take, explain:
1. What you observed
2. What action you're taking and why
3. What the expected next step is
"""

    def get_tools(self) -> list[dict[str, Any]]:
        tools = self._common_tools()
        tools.extend([
            {
                "name": "dispatch_engineer",
                "description": "Dispatch an engineer agent to work on a ticket.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "issue_number": {"type": "integer"},
                    },
                    "required": ["issue_number"],
                },
            },
            {
                "name": "dispatch_review",
                "description": "Dispatch a senior engineer to review a PR.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pr_number": {"type": "integer"},
                        "issue_number": {"type": "integer"},
                    },
                    "required": ["pr_number", "issue_number"],
                },
            },
            {
                "name": "dispatch_security",
                "description": "Dispatch security + infosec pair review for a PR.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pr_number": {"type": "integer"},
                        "issue_number": {"type": "integer"},
                    },
                    "required": ["pr_number", "issue_number"],
                },
            },
            {
                "name": "dispatch_qa",
                "description": "Dispatch QA agent for a PR after security approval.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pr_number": {"type": "integer"},
                        "issue_number": {"type": "integer"},
                    },
                    "required": ["pr_number", "issue_number"],
                },
            },
            {
                "name": "dispatch_deploy",
                "description": "Dispatch deployment after QA passes.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pr_number": {"type": "integer"},
                        "issue_number": {"type": "integer"},
                    },
                    "required": ["pr_number", "issue_number"],
                },
            },
            {
                "name": "dispatch_wildcard",
                "description": "Dispatch the wildcard codebase scanner.",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "dispatch_blog",
                "description": "Dispatch the blog writer to publish an update.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "context": {"type": "string"},
                    },
                    "required": ["topic"],
                },
            },
            {
                "name": "escalate_blocked",
                "description": "Escalate a blocked ticket by engaging additional agents.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "issue_number": {"type": "integer"},
                        "blocked_agent": {"type": "string"},
                        "block_reason": {"type": "string"},
                    },
                    "required": ["issue_number", "blocked_agent", "block_reason"],
                },
            },
        ])
        return tools

    def handle_tool_call(self, name: str, params: dict[str, Any]) -> Any:
        match name:
            case "dispatch_engineer":
                return dispatch_engineer_for_ticket(self.github, params["issue_number"])
            case "dispatch_review":
                return dispatch_review(
                    self.github, params["pr_number"], params["issue_number"]
                )
            case "dispatch_security":
                return dispatch_security_review(
                    self.github, params["pr_number"], params["issue_number"]
                )
            case "dispatch_qa":
                return dispatch_qa(
                    self.github, params["pr_number"], params["issue_number"]
                )
            case "dispatch_deploy":
                return dispatch_deploy(
                    self.github, params["pr_number"], params["issue_number"]
                )
            case "dispatch_wildcard":
                return dispatch_wildcard_scan(self.github)
            case "dispatch_blog":
                return dispatch_blog_post(
                    self.github, params["topic"], params.get("context", "")
                )
            case "escalate_blocked":
                return escalate_block(
                    self.github,
                    params["issue_number"],
                    params["blocked_agent"],
                    params["block_reason"],
                )
            case _:
                return self._handle_common_tool(name, params)

    def run(self, trigger: dict[str, Any]) -> None:
        """Main orchestrator cycle."""
        action = trigger.get("action", "cycle")

        if action == "setup":
            self._setup_labels()
            return

        if action == "escalate":
            self._handle_escalation(trigger)
            return

        # Regular cycle — scan the board and dispatch agents
        self._run_cycle()

    def _setup_labels(self) -> None:
        """Ensure all required labels exist in the repo."""
        labels = get_all_labels()
        self.github.ensure_labels(labels)
        logger.info("Created/updated %d labels", len(labels))

    def _run_cycle(self) -> None:
        """Main orchestrator cycle: scan board, dispatch agents."""
        # Build context about current board state
        ready_tickets = self.github.list_issues(labels="state:ready")
        in_progress = self.github.list_issues(labels="state:in-progress")
        blocked = self.github.list_issues(labels="state:blocked")
        code_review = self.github.list_issues(labels="state:code-review")
        security_review = self.github.list_issues(labels="state:security-review")
        qa_tickets = self.github.list_issues(labels="state:qa")
        deploying = self.github.list_issues(labels="state:deploying")

        board_summary = (
            f"## Board Status\n"
            f"- Ready: {len(ready_tickets)} tickets\n"
            f"- In Progress: {len(in_progress)} tickets\n"
            f"- Blocked: {len(blocked)} tickets\n"
            f"- Code Review: {len(code_review)} tickets\n"
            f"- Security Review: {len(security_review)} tickets\n"
            f"- QA: {len(qa_tickets)} tickets\n"
            f"- Deploying: {len(deploying)} tickets\n\n"
        )

        # Format ticket details for Claude
        ticket_details = ""
        for label, tickets in [
            ("Ready", ready_tickets),
            ("Blocked", blocked),
            ("Code Review", code_review),
            ("Security Review", security_review),
            ("QA", qa_tickets),
        ]:
            if tickets:
                ticket_details += f"### {label}\n"
                for t in tickets[:10]:  # limit per category
                    ticket_details += (
                        f"- #{t['number']}: {t['title']} "
                        f"(labels: {', '.join(l['name'] for l in t.get('labels', []))})\n"
                    )
                ticket_details += "\n"

        messages = [
            {
                "role": "user",
                "content": (
                    f"Run your orchestration cycle. Here is the current board state:\n\n"
                    f"{board_summary}\n{ticket_details}\n"
                    f"Analyze the board and take appropriate actions. Dispatch agents for "
                    f"any tickets that need attention. Escalate any blocks. Maximum 10 "
                    f"dispatches this cycle."
                ),
            }
        ]

        self.agentic_loop(messages, self.get_tools())

    def _handle_escalation(self, trigger: dict[str, Any]) -> None:
        """Handle an escalation from a blocked agent."""
        issue_number = int(trigger["issue_number"])
        blocked_agent = trigger.get("blocked_agent", "unknown")
        block_reason = trigger.get("block_reason", "unknown")

        issue = self.github.get_issue(issue_number)

        messages = [
            {
                "role": "user",
                "content": (
                    f"ESCALATION: Agent `{blocked_agent}` is blocked on #{issue_number}.\n"
                    f"Reason: {block_reason}\n\n"
                    f"Issue: {issue.get('title', 'N/A')}\n"
                    f"Body: {issue.get('body', 'N/A')[:2000]}\n\n"
                    f"Decide how to unblock this: dispatch another engineer, re-scope the "
                    f"ticket, or archive it if infeasible."
                ),
            }
        ]

        self.agentic_loop(messages, self.get_tools())
