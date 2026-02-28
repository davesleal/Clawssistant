"""PM Agent — product management, board management, user collaboration, and blog.

Responsibilities:
- Monitor GitHub issues and discussions for new feedback
- Collaborate with users via tagging to ensure maximum clarity
- Write epics, features, and user stories
- Manage board and timeline
- Coordinate with blog agent for publishing updates
"""

from __future__ import annotations

import logging
from typing import Any

from agents.base import Agent
from agents.config import AgentRole
from agents.context import TicketContext

logger = logging.getLogger("clawssistant.agents.pm")


class PMAgent(Agent):
    role = AgentRole.PM

    @property
    def system_prompt(self) -> str:
        return """You are the Product Manager Agent for the Clawssistant project — an autonomous,
open-source, Claude-powered home assistant replacing Google Home, Alexa, and Siri.

## Your Role
You are the product voice. You bridge user needs with engineering capacity. You
collaborate directly with users in GitHub issues and discussions, write clear
tickets, and manage the product roadmap.

## Core Directives
1. BE PROACTIVE — engage users, ask clarifying questions, suggest improvements.
2. BE AUTONOMOUS — write epics/features/stories without waiting for approval.
3. COLLABORATE — tag users (@username) for clarity. Ask specific questions.
4. KEEP THE BOARD CURRENT — prioritize, re-prioritize, and groom continuously.
5. WRITE FOR AGENTS — every ticket must contain enough context for an engineer
   agent to implement it without asking questions.

## Ticket Writing Standards
Every ticket you create MUST include:

### Epic Format
```
## Objective
[What we're trying to achieve and why]

## User Value
[Who benefits and how]

## Features
- [ ] Feature 1 (link to feature ticket)
- [ ] Feature 2

## Success Criteria
[How we know this epic is done]

## Dependencies
[What needs to exist first]
```

### Feature/User Story Format
```
## User Story
As a [persona], I want [goal] so that [benefit].

## Acceptance Criteria
- [ ] Given [context], when [action], then [result]
- [ ] Given [context], when [action], then [result]

## Technical Notes
[Architecture decisions, API contracts, relevant code paths]

## Scope
- IN: [what's included]
- OUT: [what's explicitly excluded]

## Priority
[P0-P4 with reasoning]

## Effort Estimate
[XS/S/M/L/XL]
```

## User Collaboration Guidelines
- Always @tag the original issue author when asking for clarification
- Ask SPECIFIC questions, not vague "can you clarify?"
- Summarize your understanding back to the user for confirmation
- If a request is unclear after 2 rounds of clarification, scope it to what IS clear
- Thank users for their feedback
- Link related issues/discussions

## Board Management
- Review and re-prioritize the backlog weekly
- Ensure no ticket sits in "ready" for more than 1 week
- Flag scope creep — split large tickets into smaller ones
- Archive tickets that are stale (>30 days with no activity)

## Blog Topics
When significant milestones are reached, request a blog post covering:
- New features shipped
- Architecture decisions made
- Community contributions
- Roadmap updates

## Safety Parameters
- Never promise timelines to users
- Never share internal agent coordination details with users
- Keep all user-facing communication professional and friendly
- Escalate toxic/abusive users to the orchestrator
"""

    def get_tools(self) -> list[dict[str, Any]]:
        tools = self._common_tools()
        tools.extend([
            {
                "name": "create_epic",
                "description": "Create an epic issue with child feature tickets.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                        "features": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "body": {"type": "string"},
                                    "priority": {"type": "string"},
                                },
                                "required": ["title", "body"],
                            },
                            "description": "Feature tickets to create under this epic",
                        },
                    },
                    "required": ["title", "body"],
                },
            },
            {
                "name": "reply_to_discussion",
                "description": "Reply to a GitHub Discussion to collaborate with users.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "discussion_number": {"type": "integer"},
                        "body": {"type": "string"},
                    },
                    "required": ["discussion_number", "body"],
                },
            },
            {
                "name": "request_blog_post",
                "description": "Request the blog agent to write and publish a post.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "context": {"type": "string"},
                    },
                    "required": ["topic"],
                },
            },
        ])
        return tools

    def handle_tool_call(self, name: str, params: dict[str, Any]) -> Any:
        match name:
            case "create_epic":
                return self._create_epic(params)
            case "reply_to_discussion":
                disc = self.github.get_discussion(params["discussion_number"])
                disc_id = disc.get("id", "")
                body = params["body"] + self.signature
                return self.github.reply_to_discussion(disc_id, body)
            case "request_blog_post":
                from agents.dispatch import dispatch_blog_post
                return dispatch_blog_post(
                    self.github, params["topic"], params.get("context", "")
                )
            case _:
                return self._handle_common_tool(name, params)

    def _create_epic(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create an epic and its child feature tickets."""
        # Create the epic issue
        epic_result = self.github.create_issue(
            title=f"[Epic] {params['title']}",
            body=params["body"],
            labels=["type:epic", "state:scoped"],
        )

        results = {"epic": epic_result, "features": []}

        # Create child feature tickets
        for feature in params.get("features", []):
            priority_label = f"priority:{feature.get('priority', 'P2-medium')}"
            body = feature["body"] + f"\n\n**Parent Epic:** {epic_result.get('url', 'N/A')}"
            feat_result = self.github.create_issue(
                title=feature["title"],
                body=body,
                labels=["type:feature", "state:backlog", priority_label],
            )
            results["features"].append(feat_result)

        return results

    def run(self, trigger: dict[str, Any]) -> None:
        """PM agent entrypoint."""
        action = trigger.get("action", "review")

        if action == "review_issue":
            self._review_issue(int(trigger["issue_number"]))
        elif action == "review_discussion":
            self._review_discussion(int(trigger["discussion_number"]))
        elif action == "groom_backlog":
            self._groom_backlog()
        else:
            self._review_issue(int(trigger.get("issue_number", 0)))

    def _review_issue(self, issue_number: int) -> None:
        """Review a new issue and collaborate with the author."""
        issue = self.github.get_issue(issue_number)
        messages = [
            {
                "role": "user",
                "content": (
                    f"A new issue has been filed. Review it and take appropriate action.\n\n"
                    f"**Issue #{issue_number}:** {issue.get('title', 'N/A')}\n"
                    f"**Author:** @{issue.get('author', {}).get('login', 'unknown')}\n"
                    f"**Body:**\n{issue.get('body', 'No description')}\n\n"
                    f"Your options:\n"
                    f"1. If clear enough → create epic/feature/story tickets and add to board\n"
                    f"2. If unclear → comment asking the author specific questions\n"
                    f"3. If duplicate → link to the existing issue and close\n"
                    f"4. If out of scope → explain why and close\n\n"
                    f"Always tag the author (@username) in your response."
                ),
            }
        ]
        self.agentic_loop(messages, self.get_tools())

    def _review_discussion(self, discussion_number: int) -> None:
        """Review a GitHub Discussion and engage with the community."""
        disc = self.github.get_discussion(discussion_number)
        messages = [
            {
                "role": "user",
                "content": (
                    f"A new discussion or comment has been posted. Engage with the user.\n\n"
                    f"**Discussion #{discussion_number}:** {disc.get('title', 'N/A')}\n"
                    f"**Author:** @{disc.get('author', {}).get('login', 'unknown')}\n"
                    f"**Body:**\n{disc.get('body', 'No content')}\n\n"
                    f"**Comments:**\n"
                    + "\n".join(
                        f"- @{c.get('author', {}).get('login', '?')}: {c.get('body', '')[:500]}"
                        for c in disc.get("comments", {}).get("nodes", [])
                    )
                    + "\n\nEngage thoughtfully. If this should become a ticket, create one."
                ),
            }
        ]
        self.agentic_loop(messages, self.get_tools())

    def _groom_backlog(self) -> None:
        """Review and groom the backlog."""
        backlog = self.github.list_issues(labels="state:backlog")
        messages = [
            {
                "role": "user",
                "content": (
                    f"Groom the backlog. There are {len(backlog)} tickets:\n\n"
                    + "\n".join(
                        f"- #{t['number']}: {t['title']}"
                        for t in backlog[:20]
                    )
                    + "\n\nReview priorities, check for stale tickets (archive if >30 days "
                    f"with no activity), and move ready tickets to 'ready' state."
                ),
            }
        ]
        self.agentic_loop(messages, self.get_tools())
