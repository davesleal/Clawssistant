"""Sr. Software Engineer Agent — code review and architecture review.

Reviews PRs for:
- Code quality and correctness
- Architecture and design patterns
- Test coverage and edge cases
- Performance and scalability
- Adherence to project standards

Can split large reviews across multiple engineer agents if needed.
"""

from __future__ import annotations

import logging
from typing import Any

from agents.base import Agent
from agents.config import AgentRole

logger = logging.getLogger("clawssistant.agents.reviewer")


class ReviewerAgent(Agent):
    role = AgentRole.SR_ENGINEER

    @property
    def system_prompt(self) -> str:
        return """You are a Senior Software Engineer Agent reviewing code for the Clawssistant
project — an autonomous, open-source, Claude-powered home assistant.

## Your Role
You are the quality gate. Nothing ships without your approval. You review PRs
for correctness, architecture, security, tests, and adherence to standards.

## Review Criteria

### 1. Correctness
- Does the code do what the ticket asks?
- Are edge cases handled?
- Are error paths correct?
- Are there race conditions or concurrency issues?

### 2. Architecture
- Does this fit the existing architecture (see CLAUDE.md)?
- Are component boundaries respected?
- Is the dependency direction correct?
- Are interfaces clean and well-defined?

### 3. Code Quality
- PEP 8 compliance, type hints everywhere
- Async/await used correctly
- No code smells (long methods, deep nesting, magic numbers)
- DRY without over-abstracting

### 4. Testing
- Are there tests for the happy path?
- Are there tests for error/edge cases?
- Is coverage adequate?
- Are tests deterministic and fast?

### 5. Security
- Input validation present?
- No eval/exec/shell=True?
- No secrets in code?
- Path traversal protection?
- SQL injection prevention?

### 6. Performance
- No unnecessary allocations or copies?
- Database queries efficient?
- No N+1 patterns?
- Appropriate use of caching?

### 7. UX (from the triad perspective)
- Are error messages helpful?
- Are API responses well-structured?
- Is configuration intuitive?

## Review Output Format
Structure your review as:

```
## Review Summary
**Verdict:** [APPROVE / REQUEST CHANGES / COMMENT]

### What's Good
- [positive observations]

### Issues Found
- 🔴 **Critical:** [must fix before merge]
- 🟡 **Suggestion:** [should fix, not blocking]
- 🔵 **Nit:** [style preference, take it or leave it]

### Architecture Notes
[any architectural observations]

### Security Notes
[any security concerns]

### Missing Tests
[tests that should be added]
```

## Decision Rules
- APPROVE: No critical issues, tests pass, security clean
- REQUEST CHANGES: Any critical issue found
- COMMENT: Only suggestions and nits, no critical issues

## If PR Is Too Large
If the PR changes >500 lines or >10 files, recommend splitting it and note
which parts you've reviewed thoroughly vs. skimmed.

## Safety Parameters
- Never approve a PR with known security vulnerabilities
- Never approve without test coverage for new functionality
- Never approve code that logs secrets or credentials
- If uncertain about security, request the security agent's input
"""

    def get_tools(self) -> list[dict[str, Any]]:
        tools = self._common_tools()
        tools.extend([
            {
                "name": "get_pr_details",
                "description": "Get full PR details including diff.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pr_number": {"type": "integer"},
                    },
                    "required": ["pr_number"],
                },
            },
            {
                "name": "get_pr_diff",
                "description": "Get the full diff of a PR.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pr_number": {"type": "integer"},
                    },
                    "required": ["pr_number"],
                },
            },
            {
                "name": "submit_review",
                "description": "Submit a review on the PR.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pr_number": {"type": "integer"},
                        "event": {
                            "type": "string",
                            "enum": ["approve", "request-changes", "comment"],
                        },
                        "body": {"type": "string"},
                    },
                    "required": ["pr_number", "event", "body"],
                },
            },
            {
                "name": "request_security_review",
                "description": "Request a security review for a PR with specific concerns.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pr_number": {"type": "integer"},
                        "issue_number": {"type": "integer"},
                        "concerns": {"type": "string"},
                    },
                    "required": ["pr_number", "issue_number"],
                },
            },
        ])
        return tools

    def handle_tool_call(self, name: str, params: dict[str, Any]) -> Any:
        match name:
            case "get_pr_details":
                return self.github.get_pr(params["pr_number"])
            case "get_pr_diff":
                diff = self.github.get_pr_diff(params["pr_number"])
                # Truncate very large diffs
                if len(diff) > 20000:
                    return diff[:20000] + "\n\n... [diff truncated, >20k chars]"
                return diff
            case "submit_review":
                body = params["body"] + self.signature
                result = self.github.review_pr(
                    params["pr_number"], params["event"], body
                )
                # Update ticket state based on review
                if params["event"] == "approve":
                    # Move to security review
                    issue_number = self._get_linked_issue(params["pr_number"])
                    if issue_number:
                        from agents.state import TicketState
                        self._transition_ticket(issue_number, TicketState.SECURITY_REVIEW)
                elif params["event"] == "request-changes":
                    issue_number = self._get_linked_issue(params["pr_number"])
                    if issue_number:
                        from agents.state import TicketState
                        self._transition_ticket(issue_number, TicketState.IN_PROGRESS)
                return result
            case "request_security_review":
                from agents.dispatch import dispatch_security_review
                return dispatch_security_review(
                    self.github, params["pr_number"], params["issue_number"]
                )
            case _:
                return self._handle_common_tool(name, params)

    def _get_linked_issue(self, pr_number: int) -> int | None:
        """Extract linked issue number from PR body."""
        pr = self.github.get_pr(pr_number)
        body = pr.get("body", "")
        import re
        match = re.search(r"(?:Closes|Fixes|Resolves)\s+#(\d+)", body, re.IGNORECASE)
        return int(match.group(1)) if match else None

    def run(self, trigger: dict[str, Any]) -> None:
        """Review a PR."""
        pr_number = int(trigger.get("pr_number", 0))
        if not pr_number:
            logger.warning("Reviewer called without pr_number")
            return

        pr = self.github.get_pr(pr_number)
        diff = self.github.get_pr_diff(pr_number)

        # Truncate diff for context
        diff_preview = diff[:15000] if len(diff) > 15000 else diff

        messages = [
            {
                "role": "user",
                "content": (
                    f"Review this PR thoroughly.\n\n"
                    f"**PR #{pr_number}:** {pr.get('title', 'N/A')}\n"
                    f"**Branch:** {pr.get('headRefName', '?')} → {pr.get('baseRefName', '?')}\n"
                    f"**Changes:** +{pr.get('additions', 0)} -{pr.get('deletions', 0)}\n"
                    f"**Files:** {len(pr.get('files', []))}\n\n"
                    f"**Description:**\n{pr.get('body', 'No description')}\n\n"
                    f"**Diff:**\n```diff\n{diff_preview}\n```\n\n"
                    f"Review from all angles (correctness, architecture, security, tests, "
                    f"performance, UX). Submit your review using submit_review."
                ),
            }
        ]

        self.agentic_loop(messages, self.get_tools())
