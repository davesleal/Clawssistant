"""QA Agent — validates deployed changes after security approval.

Runs after both security + infosec approve. Responsibilities:
- Run the full test suite
- Validate acceptance criteria from the ticket
- Check for regressions
- Exploratory testing of affected areas
- File regression bugs if found
"""

from __future__ import annotations

import logging
from typing import Any

from agents.base import Agent
from agents.config import AgentRole
from agents.context import QAResult

logger = logging.getLogger("clawssistant.agents.qa")


class QAAgent(Agent):
    role = AgentRole.QA

    @property
    def system_prompt(self) -> str:
        return """You are the QA Engineer Agent for the Clawssistant project — an autonomous,
open-source, Claude-powered home assistant.

## Your Role
You are the final quality gate before deployment. You validate that changes
meet their acceptance criteria, don't introduce regressions, and work correctly.

## QA Process

### 1. Test Suite
- Run `pytest tests/ -v` and verify all tests pass
- Check coverage hasn't decreased
- Review new tests for thoroughness

### 2. Acceptance Criteria
- Read the original ticket's acceptance criteria
- Verify each criterion is met by the implementation
- Document which criteria pass/fail

### 3. Regression Check
- Identify areas affected by the change
- Verify existing functionality still works
- Check configuration compatibility

### 4. Exploratory Testing
- Think about edge cases the developer might have missed
- Test error conditions
- Test with unusual inputs

### 5. Documentation
- Are any docs/comments outdated by the change?
- Is the README still accurate?
- Are any config examples affected?

## Report Format
```
## 🧪 QA Report

### Verdict: [PASSED / FAILED / PARTIAL]

### Test Suite
- Total: [N] tests
- Passed: [N]
- Failed: [N]
- Skipped: [N]
- Coverage: [X]%

### Acceptance Criteria
- [x] Criterion 1: [status]
- [ ] Criterion 2: [status — why it failed]

### Regression Check
- [area]: [status]

### Exploratory Findings
- [any issues discovered]

### Recommendation
[DEPLOY / SEND BACK with specific issues to fix]
```

## Decision Rules
- PASS: All tests pass, all acceptance criteria met, no regressions
- FAIL: Any test failure, acceptance criteria not met, or regression found
- PARTIAL: Tests pass but some acceptance criteria unclear/untestable

## Safety Parameters
- Never approve with failing tests
- If unsure whether a behavior is a regression, flag it for human review
- Security-sensitive changes get extra scrutiny
"""

    def get_tools(self) -> list[dict[str, Any]]:
        tools = self._common_tools()
        tools.extend([
            {
                "name": "run_tests",
                "description": "Run the full test suite.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "extra_args": {"type": "string", "description": "Additional pytest args"},
                    },
                },
            },
            {
                "name": "get_pr_details",
                "description": "Get PR details for QA context.",
                "input_schema": {
                    "type": "object",
                    "properties": {"pr_number": {"type": "integer"}},
                    "required": ["pr_number"],
                },
            },
            {
                "name": "submit_qa_result",
                "description": "Submit the QA verdict.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pr_number": {"type": "integer"},
                        "issue_number": {"type": "integer"},
                        "verdict": {
                            "type": "string",
                            "enum": ["passed", "failed", "partial"],
                        },
                        "report_body": {"type": "string"},
                        "failures": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["pr_number", "issue_number", "verdict", "report_body"],
                },
            },
            {
                "name": "file_bug",
                "description": "File a bug issue for a regression found during QA.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                        "related_pr": {"type": "integer"},
                    },
                    "required": ["title", "body"],
                },
            },
        ])
        return tools

    def handle_tool_call(self, name: str, params: dict[str, Any]) -> Any:
        match name:
            case "run_tests":
                import subprocess, os
                extra = params.get("extra_args", "")
                cmd = f"pytest tests/ -v --tb=short {extra}"
                try:
                    result = subprocess.run(
                        cmd, shell=True, capture_output=True, text=True, timeout=300,
                        cwd=os.environ.get("GITHUB_WORKSPACE", "."),
                    )
                    return {
                        "stdout": result.stdout[-5000:],
                        "stderr": result.stderr[-1000:],
                        "returncode": result.returncode,
                    }
                except subprocess.TimeoutExpired:
                    return {"error": "Tests timed out (300s)"}
            case "get_pr_details":
                return self.github.get_pr(params["pr_number"])
            case "submit_qa_result":
                return self._submit_qa(params)
            case "file_bug":
                body = params["body"]
                if params.get("related_pr"):
                    body += f"\n\nFound during QA of PR #{params['related_pr']}"
                return self.github.create_issue(
                    title=f"[Bug] {params['title']}",
                    body=body,
                    labels=["type:bug", "state:new", "found-in-qa"],
                )
            case _:
                return self._handle_common_tool(name, params)

    def _submit_qa(self, params: dict[str, Any]) -> dict[str, Any]:
        pr_number = params["pr_number"]
        issue_number = params["issue_number"]
        verdict = params["verdict"]
        body = params["report_body"] + self.signature

        # Post QA report on PR
        self.github.review_pr(
            pr_number,
            "approve" if verdict == "passed" else "request-changes",
            body,
        )

        # Update context
        context = self.read_context(issue_number)
        if context:
            result = QAResult(
                verdict=verdict,
                test_summary=params["report_body"][:500],
                failures=params.get("failures", []),
            )
            context.add_qa_result(result)
            self.post_context(issue_number, context)

        # State transition
        from agents.state import TicketState
        if verdict == "passed":
            self._transition_ticket(issue_number, TicketState.DEPLOYING)
        else:
            self._transition_ticket(issue_number, TicketState.IN_PROGRESS)

        return {"success": True, "verdict": verdict}

    def run(self, trigger: dict[str, Any]) -> None:
        pr_number = int(trigger.get("pr_number", 0))
        issue_number = int(trigger.get("issue_number", 0))

        if not pr_number:
            logger.warning("QA agent called without pr_number")
            return

        pr = self.github.get_pr(pr_number)
        issue = self.github.get_issue(issue_number) if issue_number else {}

        messages = [
            {
                "role": "user",
                "content": (
                    f"Run QA on this PR.\n\n"
                    f"**PR #{pr_number}:** {pr.get('title', 'N/A')}\n"
                    f"**Description:**\n{pr.get('body', 'No description')}\n\n"
                    f"**Original Ticket #{issue_number}:**\n"
                    f"{issue.get('body', 'No ticket body')}\n\n"
                    f"Steps:\n"
                    f"1. Run the full test suite\n"
                    f"2. Check each acceptance criterion from the ticket\n"
                    f"3. Assess for regressions\n"
                    f"4. Submit your QA verdict\n"
                    f"5. File bugs for any regressions found"
                ),
            }
        ]

        self.agentic_loop(messages, self.get_tools())
