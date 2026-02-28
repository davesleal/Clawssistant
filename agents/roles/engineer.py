"""Engineer Agent — develops tickets, persists until deployed or archived.

Key behaviors:
- Creates a feature branch and writes code
- Opens a PR when implementation is ready
- If blocked, engages other engineers via the orchestrator
- Persists on a ticket through the entire review cycle
- Never abandons a ticket — stays assigned until deployed or archived
"""

from __future__ import annotations

import logging
import subprocess
import os
from typing import Any

from agents.base import Agent
from agents.config import AgentRole
from agents.context import TicketContext

logger = logging.getLogger("clawssistant.agents.engineer")


class EngineerAgent(Agent):
    role = AgentRole.ENGINEER

    @property
    def system_prompt(self) -> str:
        return """You are a Development Engineer Agent for the Clawssistant project — an autonomous,
open-source, Claude-powered home assistant.

## Your Role
You are a skilled Python developer. You take tickets from the board, write high-quality
code, create PRs, and persist on each ticket until it is deployed or archived.

## Core Directives
1. BE PROACTIVE — read the ticket fully, plan your approach, then execute.
2. WRITE CLEAN CODE — follow PEP 8, use type hints, write tests, format with ruff.
3. PERSIST — you own this ticket until it's done. Address review feedback promptly.
4. ESCALATE BLOCKS — if you're stuck, immediately signal the orchestrator. Don't spin.
5. COMPLETE CONTEXT — your PR description must be detailed enough for the reviewer.

## Development Workflow
1. Read the ticket thoroughly — understand acceptance criteria
2. Read related code in the codebase to understand patterns
3. Plan your implementation (what files, what changes)
4. Write the code in small, logical steps
5. Write tests for your changes
6. Run the test suite locally
7. Create a PR with a detailed description
8. Address review feedback until approved

## Code Standards (from CLAUDE.md)
- Python 3.12+, type hints everywhere
- Async/await for all I/O
- Format with ruff (line length 100)
- Tests required (pytest + pytest-asyncio)
- No eval(), exec(), subprocess(shell=True) without security review
- Validate all external input
- Never log secrets or API keys

## PR Description Template
```
## Summary
[What this PR does and why]

## Changes
- [File 1]: [what changed]
- [File 2]: [what changed]

## Testing
- [What tests were added/modified]
- [How to manually test]

## Ticket
Closes #[issue_number]

## Checklist
- [ ] Tests pass
- [ ] Ruff check passes
- [ ] Type hints complete
- [ ] No security concerns
- [ ] Acceptance criteria met
```

## When Blocked
If you encounter a block (missing dependency, unclear requirement, architecture
question), IMMEDIATELY:
1. Comment on the issue explaining the block
2. Call the signal_block tool to notify the orchestrator
3. Wait for guidance — do not guess or make risky assumptions

## Safety Parameters
- Never commit secrets, API keys, or credentials
- Never use force push
- Always create a new branch (never push to main directly)
- Run tests before opening a PR
- If you're unsure about a security implication, flag it
"""

    def get_tools(self) -> list[dict[str, Any]]:
        tools = self._common_tools()
        tools.extend([
            {
                "name": "read_file",
                "description": "Read a file from the repository.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path relative to repo root"},
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "write_file",
                "description": "Write content to a file.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            },
            {
                "name": "list_files",
                "description": "List files in a directory.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path"},
                        "pattern": {"type": "string", "description": "Glob pattern"},
                    },
                },
            },
            {
                "name": "run_command",
                "description": "Run a shell command (e.g., tests, linting).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                    },
                    "required": ["command"],
                },
            },
            {
                "name": "git_create_branch",
                "description": "Create and switch to a new branch.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "branch_name": {"type": "string"},
                    },
                    "required": ["branch_name"],
                },
            },
            {
                "name": "git_commit_and_push",
                "description": "Stage all changes, commit, and push.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                        "branch": {"type": "string"},
                    },
                    "required": ["message", "branch"],
                },
            },
            {
                "name": "create_pr",
                "description": "Create a pull request.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                        "head": {"type": "string", "description": "Branch name"},
                        "base": {"type": "string", "description": "Target branch"},
                    },
                    "required": ["title", "body", "head"],
                },
            },
            {
                "name": "signal_block",
                "description": "Signal that you're blocked and need help from orchestrator.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "issue_number": {"type": "integer"},
                        "reason": {"type": "string"},
                    },
                    "required": ["issue_number", "reason"],
                },
            },
        ])
        return tools

    def handle_tool_call(self, name: str, params: dict[str, Any]) -> Any:
        match name:
            case "read_file":
                return self._read_file(params["path"])
            case "write_file":
                return self._write_file(params["path"], params["content"])
            case "list_files":
                return self._list_files(params.get("path", "."), params.get("pattern", "*"))
            case "run_command":
                return self._run_command(params["command"])
            case "git_create_branch":
                return self._git_create_branch(params["branch_name"])
            case "git_commit_and_push":
                return self._git_commit_push(params["message"], params["branch"])
            case "create_pr":
                return self.github.create_pr(
                    title=params["title"],
                    body=params["body"],
                    head=params["head"],
                    base=params.get("base", "main"),
                    labels=["state:code-review"],
                )
            case "signal_block":
                from agents.dispatch import escalate_block
                self._transition_ticket(params["issue_number"],
                                        __import__("agents.state", fromlist=["TicketState"]).TicketState.BLOCKED)
                return escalate_block(
                    self.github, params["issue_number"], "engineer", params["reason"]
                )
            case _:
                return self._handle_common_tool(name, params)

    def _read_file(self, path: str) -> dict[str, Any]:
        """Read a file safely — no path traversal."""
        from pathlib import PurePosixPath
        normalized = str(PurePosixPath(path))
        if normalized.startswith("/") or ".." in normalized:
            return {"error": "Path traversal detected"}
        try:
            with open(path) as f:
                return {"content": f.read(), "path": path}
        except FileNotFoundError:
            return {"error": f"File not found: {path}"}
        except OSError as e:
            return {"error": str(e)}

    def _write_file(self, path: str, content: str) -> dict[str, Any]:
        """Write a file safely."""
        from pathlib import PurePosixPath, Path
        normalized = str(PurePosixPath(path))
        if normalized.startswith("/") or ".." in normalized:
            return {"error": "Path traversal detected"}
        # Don't write secrets
        for secret_pattern in [".env", "secrets.yaml", "credentials"]:
            if secret_pattern in path.lower():
                return {"error": f"Refusing to write to potential secret file: {path}"}
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            return {"success": True, "path": path}
        except OSError as e:
            return {"error": str(e)}

    def _list_files(self, path: str, pattern: str) -> dict[str, Any]:
        """List files matching a pattern."""
        from pathlib import Path
        try:
            files = sorted(str(p) for p in Path(path).glob(pattern) if p.is_file())
            return {"files": files[:100]}  # limit output
        except OSError as e:
            return {"error": str(e)}

    def _run_command(self, command: str) -> dict[str, Any]:
        """Run a safe command — only allow known safe commands."""
        allowed_prefixes = ["pytest", "ruff", "mypy", "python -m pytest", "python -m ruff"]
        if not any(command.strip().startswith(p) for p in allowed_prefixes):
            return {"error": f"Command not in allowlist. Allowed: {allowed_prefixes}"}
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=120,
                cwd=os.environ.get("GITHUB_WORKSPACE", "."),
            )
            return {
                "stdout": result.stdout[-3000:],  # truncate
                "stderr": result.stderr[-1000:],
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"error": "Command timed out (120s)"}

    def _git_create_branch(self, branch_name: str) -> dict[str, Any]:
        """Create and checkout a new branch."""
        try:
            subprocess.run(["git", "checkout", "-b", branch_name], check=True,
                           capture_output=True, text=True)
            return {"success": True, "branch": branch_name}
        except subprocess.CalledProcessError as e:
            return {"error": e.stderr}

    def _git_commit_push(self, message: str, branch: str) -> dict[str, Any]:
        """Stage, commit, and push."""
        try:
            subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", message], check=True, capture_output=True)
            subprocess.run(["git", "push", "-u", "origin", branch], check=True,
                           capture_output=True, text=True)
            return {"success": True}
        except subprocess.CalledProcessError as e:
            return {"error": e.stderr}

    def run(self, trigger: dict[str, Any]) -> None:
        """Engineer agent entrypoint — develop a ticket."""
        issue_number = int(trigger.get("issue_number", 0))
        action = trigger.get("action", "develop")

        if not issue_number:
            logger.warning("Engineer agent called without issue_number")
            return

        issue = self.github.get_issue(issue_number)
        context = self.read_context(issue_number)

        # Update state to in-progress
        self.github.remove_labels(issue_number, ["state:ready", "state:backlog"])
        self.github.add_labels(issue_number, ["state:in-progress", "agent:engineer"])

        if action == "develop":
            self._develop(issue_number, issue, context)
        elif action == "address_feedback":
            self._address_feedback(issue_number, issue, context)

    def _develop(
        self, issue_number: int, issue: dict, context: TicketContext | None
    ) -> None:
        """Develop the ticket from scratch."""
        ctx_str = ""
        if context:
            ctx_str = (
                f"\n## Triage Context\n"
                f"- Priority: {context.priority}\n"
                f"- Scope: {context.scope_estimate}\n"
                f"- Effort: {context.estimated_effort_hours}h\n"
                f"- Type: {context.ticket_type}\n"
            )

        messages = [
            {
                "role": "user",
                "content": (
                    f"You are assigned to develop this ticket. Read the codebase, plan "
                    f"your approach, implement the changes, write tests, and open a PR.\n\n"
                    f"**Issue #{issue_number}:** {issue.get('title', 'N/A')}\n"
                    f"**Body:**\n{issue.get('body', 'No description')}\n"
                    f"{ctx_str}\n"
                    f"Steps:\n"
                    f"1. Read relevant code to understand the codebase\n"
                    f"2. Create a branch named `feature/{issue_number}-<short-description>`\n"
                    f"3. Implement the changes\n"
                    f"4. Write tests\n"
                    f"5. Run tests and linting\n"
                    f"6. Commit and push\n"
                    f"7. Create a PR\n\n"
                    f"If blocked at any point, use signal_block immediately."
                ),
            }
        ]

        self.agentic_loop(messages, self.get_tools())

    def _address_feedback(
        self, issue_number: int, issue: dict, context: TicketContext | None
    ) -> None:
        """Address review feedback on an existing PR."""
        pr_number = context.pr_number if context else None
        if not pr_number:
            logger.warning("No PR number in context for feedback")
            return

        pr = self.github.get_pr(pr_number)
        reviews = pr.get("reviews", [])

        messages = [
            {
                "role": "user",
                "content": (
                    f"Your PR #{pr_number} received review feedback. Address it.\n\n"
                    f"**Issue #{issue_number}:** {issue.get('title', 'N/A')}\n"
                    f"**Reviews:**\n"
                    + "\n".join(
                        f"- {r.get('author', {}).get('login', '?')} ({r.get('state', '?')}): "
                        f"{r.get('body', '')[:500]}"
                        for r in reviews
                    )
                    + f"\n\nRead the feedback, make the requested changes, run tests, "
                    f"commit and push to the same branch."
                ),
            }
        ]

        self.agentic_loop(messages, self.get_tools())
