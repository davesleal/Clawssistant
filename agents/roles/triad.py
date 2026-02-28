"""Triad Squad — the executing task force.

Three engineers work as a unit on every ticket:
- Design Engineer: architecture, system design, API contracts, data models
- Software Engineer: implementation, tests, code quality
- UX Engineer: user experience, accessibility, CLI/API ergonomics, docs

The triad collaborates through a shared conversation. All three perspectives
must be satisfied before a PR is opened. This ensures every change is
well-designed, well-built, and well-experienced.
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Any

from agents.base import Agent
from agents.config import AgentRole
from agents.context import TicketContext

logger = logging.getLogger("clawssistant.agents.triad")


class TriadSquadAgent(Agent):
    """Triad Squad — design engineer, software engineer, and UX engineer as one unit.

    This agent embodies all three perspectives in a single Claude conversation,
    using a carefully structured system prompt that forces all three viewpoints
    to be considered for every decision.
    """

    role = AgentRole.ENGINEER  # Uses engineer role for dispatch/config

    @property
    def system_prompt(self) -> str:
        return """You are a TRIAD SQUAD — three engineers working as a single unit on the
Clawssistant project (an autonomous, open-source, Claude-powered home assistant).

You embody THREE distinct engineering perspectives simultaneously. Every decision,
every line of code, every interface must satisfy all three.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🏗️ DESIGN ENGINEER (DE)
You think about ARCHITECTURE and SYSTEM DESIGN:
- Data models and schemas
- API contracts and interfaces
- Component boundaries and dependency flow
- Scalability and extensibility
- Design patterns and architectural consistency
- Integration points between subsystems

Before writing code, always ask:
"Is the architecture clean? Will this scale? Does this fit the system?"

## 💻 SOFTWARE ENGINEER (SE)
You think about IMPLEMENTATION and QUALITY:
- Clean, tested, production-ready Python code
- Type hints, async patterns, error handling
- Test coverage and edge cases
- Performance and efficiency
- Security (OWASP top 10, input validation, no secrets)
- Code style (PEP 8, ruff, line length 100)

Before committing, always ask:
"Is this correct, secure, tested, and maintainable?"

## 🎨 UX ENGINEER (UXE)
You think about USER EXPERIENCE and DEVELOPER EXPERIENCE:
- CLI output formatting and feedback
- API response shapes and error messages
- Configuration file ergonomics
- Documentation clarity
- Accessibility of voice commands
- Onboarding and setup experience
- Error messages that help users fix the problem

Before shipping, always ask:
"Would a user/developer understand this? Is it pleasant to use?"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## How You Work

### Planning Phase
When you receive a ticket:
1. **DE** proposes the architecture — what components, what interfaces
2. **SE** evaluates feasibility — what's realistic, what's risky
3. **UXE** evaluates UX — how users interact with this
4. All three agree on the approach before coding starts

Format your planning as:
```
### 🏗️ DE: Architecture Plan
[design decisions]

### 💻 SE: Implementation Plan
[technical approach]

### 🎨 UXE: Experience Plan
[UX considerations]

### ✅ Triad Consensus
[agreed approach]
```

### Implementation Phase
While coding, continuously apply all three lenses:
- DE ensures the code follows the agreed architecture
- SE ensures the code is clean, tested, and secure
- UXE ensures the interfaces are ergonomic

### Review Phase (Self-Review Before PR)
Before opening a PR, do an internal triad review:
- DE: "Does this match our architecture? Any design debt?"
- SE: "Are tests comprehensive? Any security issues? Is it performant?"
- UXE: "Are error messages helpful? Is the API/CLI intuitive?"

### PR Description
Include all three perspectives:
```
## 🏗️ Architecture
[what was designed and why]

## 💻 Implementation
[what was built and how]

## 🎨 User Experience
[how this affects users/developers]
```

## Development Standards (from CLAUDE.md)
- Python 3.12+, type hints everywhere
- Async/await for all I/O
- Format with ruff (line length 100)
- Tests required (pytest + pytest-asyncio)
- No eval(), exec(), subprocess(shell=True) without security review
- Validate all external input
- Never log secrets or API keys

## Persistence
You OWN this ticket until it's deployed or archived. Address all review feedback
from the sr-engineer, security, and QA agents. Never abandon a ticket.

## When Blocked
If ANY member of the triad is blocked:
1. Comment on the issue explaining which perspective is blocked and why
2. Signal the orchestrator for help
3. Continue working on unblocked aspects if possible
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
                        "path": {"type": "string"},
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
                        "path": {"type": "string"},
                        "pattern": {"type": "string"},
                    },
                },
            },
            {
                "name": "search_code",
                "description": "Search for a pattern in the codebase.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Regex pattern to search"},
                        "path": {"type": "string", "description": "Directory to search in"},
                        "file_type": {"type": "string", "description": "File extension (e.g. py)"},
                    },
                    "required": ["pattern"],
                },
            },
            {
                "name": "run_command",
                "description": "Run a safe command (tests, linting, type checking).",
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
                "description": "Create and switch to a new feature branch.",
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
                "description": "Stage, commit, and push changes.",
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
                "description": "Create a pull request with triad context.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                        "head": {"type": "string"},
                        "base": {"type": "string"},
                        "issue_number": {"type": "integer"},
                    },
                    "required": ["title", "body", "head"],
                },
            },
            {
                "name": "signal_block",
                "description": "Signal that the triad is blocked and needs help.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "issue_number": {"type": "integer"},
                        "blocked_perspective": {
                            "type": "string",
                            "enum": ["design", "software", "ux", "all"],
                        },
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
            case "search_code":
                return self._search_code(
                    params["pattern"], params.get("path", "."), params.get("file_type", "")
                )
            case "run_command":
                return self._run_command(params["command"])
            case "git_create_branch":
                return self._git_create_branch(params["branch_name"])
            case "git_commit_and_push":
                return self._git_commit_push(params["message"], params["branch"])
            case "create_pr":
                result = self.github.create_pr(
                    title=params["title"],
                    body=params["body"],
                    head=params["head"],
                    base=params.get("base", "main"),
                    labels=["state:code-review", "triad-squad"],
                )
                # Update ticket state
                if params.get("issue_number"):
                    from agents.state import TicketState
                    self._transition_ticket(params["issue_number"], TicketState.CODE_REVIEW)
                return result
            case "signal_block":
                perspective = params.get("blocked_perspective", "all")
                from agents.dispatch import escalate_block
                from agents.state import TicketState
                self._transition_ticket(params["issue_number"], TicketState.BLOCKED)
                return escalate_block(
                    self.github,
                    params["issue_number"],
                    f"triad-{perspective}",
                    params["reason"],
                )
            case _:
                return self._handle_common_tool(name, params)

    # ------------------------------------------------------------------
    # File operations (same security as engineer.py)
    # ------------------------------------------------------------------

    def _read_file(self, path: str) -> dict[str, Any]:
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
        from pathlib import PurePosixPath, Path
        normalized = str(PurePosixPath(path))
        if normalized.startswith("/") or ".." in normalized:
            return {"error": "Path traversal detected"}
        for secret in [".env", "secrets.yaml", "credentials"]:
            if secret in path.lower():
                return {"error": f"Refusing to write to potential secret file: {path}"}
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            return {"success": True, "path": path}
        except OSError as e:
            return {"error": str(e)}

    def _list_files(self, path: str, pattern: str) -> dict[str, Any]:
        from pathlib import Path
        try:
            files = sorted(str(p) for p in Path(path).glob(pattern) if p.is_file())
            return {"files": files[:100]}
        except OSError as e:
            return {"error": str(e)}

    def _search_code(self, pattern: str, path: str, file_type: str) -> dict[str, Any]:
        """Search codebase using grep."""
        cmd = ["grep", "-rn", pattern, path]
        if file_type:
            cmd.extend(["--include", f"*.{file_type}"])
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            lines = result.stdout.strip().split("\n")[:50]  # limit results
            return {"matches": lines, "count": len(lines)}
        except subprocess.TimeoutExpired:
            return {"error": "Search timed out"}

    def _run_command(self, command: str) -> dict[str, Any]:
        allowed = ["pytest", "ruff", "mypy", "python -m pytest", "python -m ruff"]
        if not any(command.strip().startswith(p) for p in allowed):
            return {"error": f"Command not in allowlist: {allowed}"}
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=120,
                cwd=os.environ.get("GITHUB_WORKSPACE", "."),
            )
            return {
                "stdout": result.stdout[-3000:],
                "stderr": result.stderr[-1000:],
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"error": "Command timed out (120s)"}

    def _git_create_branch(self, branch_name: str) -> dict[str, Any]:
        try:
            subprocess.run(["git", "checkout", "-b", branch_name],
                           check=True, capture_output=True, text=True)
            return {"success": True, "branch": branch_name}
        except subprocess.CalledProcessError as e:
            return {"error": e.stderr}

    def _git_commit_push(self, message: str, branch: str) -> dict[str, Any]:
        try:
            subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", message],
                           check=True, capture_output=True)
            subprocess.run(["git", "push", "-u", "origin", branch],
                           check=True, capture_output=True, text=True)
            return {"success": True}
        except subprocess.CalledProcessError as e:
            return {"error": e.stderr}

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self, trigger: dict[str, Any]) -> None:
        """Triad squad entrypoint."""
        issue_number = int(trigger.get("issue_number", 0))
        action = trigger.get("action", "develop")

        if not issue_number:
            logger.warning("Triad squad called without issue_number")
            return

        issue = self.github.get_issue(issue_number)
        context = self.read_context(issue_number)

        # Update state
        self.github.remove_labels(issue_number, ["state:ready", "state:backlog", "state:blocked"])
        self.github.add_labels(issue_number, ["state:in-progress", "agent:engineer", "triad-squad"])

        if action in ("develop", "address_feedback"):
            ctx_str = ""
            if context:
                ctx_str = (
                    f"\n## Triage Context\n"
                    f"- Priority: {context.priority}\n"
                    f"- Scope: {context.scope_estimate}\n"
                    f"- Effort: {context.estimated_effort_hours}h\n"
                    f"- Type: {context.ticket_type}\n"
                )

            if action == "address_feedback" and context and context.pr_number:
                pr = self.github.get_pr(context.pr_number)
                reviews_str = "\n".join(
                    f"- {r.get('author', {}).get('login', '?')} ({r.get('state', '?')}): "
                    f"{r.get('body', '')[:500]}"
                    for r in pr.get("reviews", [])
                )
                extra = (
                    f"\n## Review Feedback (PR #{context.pr_number})\n"
                    f"{reviews_str}\n\n"
                    f"Address all feedback, then push to the existing branch."
                )
            else:
                extra = ""

            messages = [
                {
                    "role": "user",
                    "content": (
                        f"TRIAD SQUAD: You are assigned to {'address feedback on' if action == 'address_feedback' else 'develop'} "
                        f"this ticket.\n\n"
                        f"**Issue #{issue_number}:** {issue.get('title', 'N/A')}\n"
                        f"**Body:**\n{issue.get('body', 'No description')}\n"
                        f"{ctx_str}{extra}\n\n"
                        f"Follow the triad process:\n"
                        f"1. 🏗️ DE designs the architecture\n"
                        f"2. 💻 SE plans the implementation\n"
                        f"3. 🎨 UXE evaluates the user experience\n"
                        f"4. ✅ Reach consensus\n"
                        f"5. Implement with all three lenses active\n"
                        f"6. Self-review from all three perspectives\n"
                        f"7. Create a PR with triad-structured description\n\n"
                        f"If blocked, signal immediately with which perspective is stuck."
                    ),
                }
            ]

            self.agentic_loop(messages, self.get_tools())
