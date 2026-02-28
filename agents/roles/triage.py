"""Triage Agent — multi-perspective issue evaluation.

Combines the perspectives of:
- Senior User Researcher: user need, usability, market fit
- Data Scientist: scope, effort estimation, priority scoring
- Engineer: technical feasibility, architecture impact, risk

Produces a structured triage decision: accepted, rejected, or needs-info.
"""

from __future__ import annotations

import logging
from typing import Any

from agents.base import Agent
from agents.config import AgentRole
from agents.context import TicketContext

logger = logging.getLogger("clawssistant.agents.triage")


class TriageAgent(Agent):
    role = AgentRole.TRIAGE

    @property
    def system_prompt(self) -> str:
        return """You are the Triage Agent for the Clawssistant project — an autonomous,
open-source, Claude-powered home assistant.

## Your Role
You evaluate new issues and feature requests from THREE perspectives simultaneously,
then make a triage decision.

## Three Perspectives

### 1. Senior User Researcher
Evaluate from the USER's perspective:
- Does this solve a real user problem?
- How many users would benefit?
- Is it aligned with our core principles (local-first, privacy, open)?
- Competitive analysis: how do Google Home/Alexa/Apple Home handle this?
- Usability implications

### 2. Data Scientist
Evaluate with DATA and metrics:
- Scope estimate (XS/S/M/L/XL)
- Effort in hours
- Priority score using: Impact (1-5) × Urgency (1-5) ÷ Effort (1-5)
- Alignment with current phase/roadmap
- Risk assessment (technical, scope creep, dependency)

### 3. Engineer
Evaluate TECHNICAL feasibility:
- Can this be built with the current architecture?
- What components are affected?
- Dependencies on external systems?
- Security implications?
- Performance implications?
- Estimated LOC / files changed

## Output Format
Produce a structured triage report, then take action:

```
## Triage Report

### User Research Assessment
[researcher findings]
User Need Score: [1-5]

### Data Analysis
Scope: [XS/S/M/L/XL]
Effort: [hours]
Priority Score: [calculated]
Risk: [low/medium/high]

### Technical Feasibility
Feasible: [yes/no/with-modifications]
Architecture Impact: [none/low/medium/high]
Security Implications: [none/low/medium/high]

### Decision
**Verdict:** [ACCEPTED / REJECTED / NEEDS-INFO]
**Reasoning:** [why]
**Priority:** [P0-P4]
**Recommended Type:** [epic/feature/user-story/bug/chore]
```

## After Decision
- If ACCEPTED: Create the appropriate ticket(s), label and add to backlog
- If REJECTED: Comment with detailed reasoning, close the issue
- If NEEDS-INFO: Comment asking specific questions, tag the author

## Safety Parameters
- Be honest about what's feasible — don't over-promise
- Flag security concerns immediately (label with type:security)
- If effort > XL, recommend splitting into smaller tickets
"""

    def get_tools(self) -> list[dict[str, Any]]:
        tools = self._common_tools()
        tools.append({
            "name": "post_triage_report",
            "description": "Post a structured triage report on an issue and update its state.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "issue_number": {"type": "integer"},
                    "verdict": {
                        "type": "string",
                        "enum": ["accepted", "rejected", "needs-info"],
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["P0-critical", "P1-high", "P2-medium", "P3-low", "P4-backlog"],
                    },
                    "ticket_type": {
                        "type": "string",
                        "enum": ["epic", "feature", "user-story", "bug", "chore"],
                    },
                    "scope": {
                        "type": "string",
                        "enum": ["XS", "S", "M", "L", "XL"],
                    },
                    "effort_hours": {"type": "number"},
                    "report_body": {
                        "type": "string",
                        "description": "The full triage report in markdown",
                    },
                },
                "required": ["issue_number", "verdict", "report_body"],
            },
        })
        return tools

    def handle_tool_call(self, name: str, params: dict[str, Any]) -> Any:
        if name == "post_triage_report":
            return self._post_triage_report(params)
        return self._handle_common_tool(name, params)

    def _post_triage_report(self, params: dict[str, Any]) -> dict[str, Any]:
        """Post triage report and update issue state/labels."""
        issue_number = params["issue_number"]
        verdict = params["verdict"]
        report = params["report_body"] + self.signature

        # Post the report
        self.github.comment_on_issue(issue_number, report)

        # Update labels based on verdict
        labels_to_add = [f"state:{'scoped' if verdict == 'accepted' else 'triaging'}"]

        if verdict == "accepted":
            if params.get("priority"):
                labels_to_add.append(f"priority:{params['priority']}")
            if params.get("ticket_type"):
                labels_to_add.append(f"type:{params['ticket_type']}")
            if params.get("scope"):
                labels_to_add.append(f"scope:{params['scope']}")

        self.github.remove_labels(issue_number, ["state:new", "state:triaging"])
        self.github.add_labels(issue_number, labels_to_add)

        if verdict == "rejected":
            self.github.close_issue(issue_number, reason="not_planned")

        # Save context for handoff
        ctx = TicketContext(
            ticket_id=issue_number,
            triage_decision=verdict,
            priority=params.get("priority", ""),
            scope_estimate=params.get("scope", ""),
            estimated_effort_hours=params.get("effort_hours", 0),
            ticket_type=params.get("ticket_type", ""),
            state="scoped" if verdict == "accepted" else "triaging",
        )
        self.post_context(issue_number, ctx)

        return {"success": True, "verdict": verdict}

    def run(self, trigger: dict[str, Any]) -> None:
        """Triage an issue or discussion."""
        issue_number = int(trigger.get("issue_number", 0))
        if not issue_number:
            logger.warning("Triage agent called without issue_number")
            return

        issue = self.github.get_issue(issue_number)

        # Mark as triaging
        self.github.add_labels(issue_number, ["state:triaging"])
        self.github.remove_labels(issue_number, ["state:new"])

        messages = [
            {
                "role": "user",
                "content": (
                    f"Triage this issue from all three perspectives (researcher, data "
                    f"scientist, engineer), then make a decision.\n\n"
                    f"**Issue #{issue_number}:** {issue.get('title', 'N/A')}\n"
                    f"**Author:** @{issue.get('author', {}).get('login', 'unknown')}\n"
                    f"**Body:**\n{issue.get('body', 'No description')}\n\n"
                    f"**Existing labels:** "
                    f"{', '.join(l['name'] for l in issue.get('labels', []))}\n\n"
                    f"**Comments:**\n"
                    + "\n".join(
                        f"- @{c.get('author', {}).get('login', '?')}: "
                        f"{c.get('body', '')[:500]}"
                        for c in issue.get("comments", [])
                    )
                    + "\n\nPost your triage report using the post_triage_report tool."
                ),
            }
        ]

        self.agentic_loop(messages, self.get_tools())
