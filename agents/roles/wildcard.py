"""Wildcard Agent — periodic codebase auditor.

Scans the entire codebase on a schedule for:
- Technical debt
- Security issues
- Dead code
- Architectural drift
- Dependency staleness
- Missing tests
- Documentation gaps
- Performance anti-patterns

Files issues for any findings.
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Any

from agents.base import Agent
from agents.config import AgentRole

logger = logging.getLogger("clawssistant.agents.wildcard")


class WildcardAgent(Agent):
    role = AgentRole.WILDCARD

    @property
    def system_prompt(self) -> str:
        return """You are the Wildcard Auditor Agent for the Clawssistant project — an autonomous,
open-source, Claude-powered home assistant.

## Your Role
You are the independent auditor. You scan the ENTIRE codebase periodically for
issues that slip through normal development. You have no bias toward any feature
or decision — you evaluate everything objectively.

## What You Scan For

### 1. Security Issues
- Hardcoded secrets or credentials
- Insecure function calls (eval, exec, shell=True)
- Missing input validation
- Dependency vulnerabilities
- Permission issues

### 2. Technical Debt
- Code duplication
- Overly complex functions (cyclomatic complexity)
- Missing type hints
- Inconsistent patterns
- TODO/FIXME/HACK comments that have been there too long

### 3. Dead Code
- Unused imports
- Unreachable code
- Unused functions/classes
- Stale test fixtures

### 4. Architecture
- Circular dependencies
- Layer violations (e.g. voice layer importing from API layer)
- Missing abstractions
- Over-engineering

### 5. Testing
- Modules without test coverage
- Tests that don't actually test anything meaningful
- Missing integration tests for critical paths
- Flaky test patterns

### 6. Documentation
- Outdated docstrings
- Missing README sections
- Stale architecture diagrams
- Undocumented configuration options

### 7. Performance
- N+1 query patterns
- Unnecessary blocking I/O in async code
- Memory leaks (unclosed connections, growing buffers)
- Missing caching opportunities

### 8. Dependencies
- Outdated packages
- Unused dependencies
- Security advisories

## Output Format
For each finding, create a GitHub issue with:
- Clear title: `[Wildcard] {category}: {finding}`
- Severity: critical / high / medium / low / informational
- File(s) and line(s) affected
- Recommendation for fixing
- Priority suggestion

## Safety Parameters
- Read-only — never modify code, only observe and report
- Don't create duplicate issues — check existing issues first
- Limit to 10 issues per scan to avoid noise
- Focus on actionable findings, not stylistic preferences
"""

    def get_tools(self) -> list[dict[str, Any]]:
        tools = self._common_tools()
        tools.extend([
            {
                "name": "scan_directory",
                "description": "List all files in a directory tree.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "pattern": {"type": "string"},
                    },
                },
            },
            {
                "name": "read_file",
                "description": "Read a file's contents.",
                "input_schema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
            {
                "name": "search_pattern",
                "description": "Search for a regex pattern across the codebase.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string"},
                        "file_type": {"type": "string"},
                    },
                    "required": ["pattern"],
                },
            },
            {
                "name": "run_linter",
                "description": "Run ruff or other linting tools.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "tool": {
                            "type": "string",
                            "enum": ["ruff", "mypy", "pip-audit"],
                        },
                    },
                    "required": ["tool"],
                },
            },
            {
                "name": "file_finding",
                "description": "Create a GitHub issue for a finding.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": [
                                "security", "tech-debt", "dead-code", "architecture",
                                "testing", "documentation", "performance", "dependency",
                            ],
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low", "informational"],
                        },
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                    },
                    "required": ["category", "severity", "title", "body"],
                },
            },
        ])
        return tools

    def handle_tool_call(self, name: str, params: dict[str, Any]) -> Any:
        match name:
            case "scan_directory":
                from pathlib import Path
                path = params.get("path", ".")
                pattern = params.get("pattern", "**/*.py")
                try:
                    files = sorted(str(p) for p in Path(path).glob(pattern) if p.is_file())
                    return {"files": files[:200]}
                except OSError as e:
                    return {"error": str(e)}
            case "read_file":
                try:
                    with open(params["path"]) as f:
                        return {"content": f.read()[:10000]}
                except (FileNotFoundError, OSError) as e:
                    return {"error": str(e)}
            case "search_pattern":
                cmd = ["grep", "-rn", params["pattern"], "."]
                if params.get("file_type"):
                    cmd.extend(["--include", f"*.{params['file_type']}"])
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    lines = result.stdout.strip().split("\n")[:50]
                    return {"matches": lines}
                except subprocess.TimeoutExpired:
                    return {"error": "Search timed out"}
            case "run_linter":
                tool = params["tool"]
                cmds = {"ruff": "ruff check .", "mypy": "mypy clawssistant/", "pip-audit": "pip-audit"}
                cmd = cmds.get(tool, "echo 'unknown tool'")
                try:
                    result = subprocess.run(
                        cmd, shell=True, capture_output=True, text=True, timeout=120,
                        cwd=os.environ.get("GITHUB_WORKSPACE", "."),
                    )
                    return {"stdout": result.stdout[-5000:], "returncode": result.returncode}
                except subprocess.TimeoutExpired:
                    return {"error": "Linter timed out"}
            case "file_finding":
                # Check for duplicates first
                existing = self.github.list_issues(labels=f"wildcard,{params['category']}")
                for issue in existing:
                    if params["title"].lower() in issue.get("title", "").lower():
                        return {"skipped": "Duplicate finding already exists"}
                return self.github.create_issue(
                    title=f"[Wildcard] {params['title']}",
                    body=(
                        f"**Category:** {params['category']}\n"
                        f"**Severity:** {params['severity']}\n\n"
                        f"{params['body']}"
                    ),
                    labels=["wildcard", f"type:{params['category']}", f"severity:{params['severity']}"],
                )
            case _:
                return self._handle_common_tool(name, params)

    def run(self, trigger: dict[str, Any]) -> None:
        """Run a codebase scan."""
        messages = [
            {
                "role": "user",
                "content": (
                    "Run your periodic codebase audit. Scan for security issues, "
                    "tech debt, dead code, architecture problems, testing gaps, "
                    "documentation issues, performance problems, and dependency "
                    "staleness.\n\n"
                    "Steps:\n"
                    "1. List all source files\n"
                    "2. Run ruff and mypy\n"
                    "3. Search for common anti-patterns (eval, exec, shell=True, "
                    "   hardcoded passwords, TODO/FIXME)\n"
                    "4. Read key files and evaluate architecture\n"
                    "5. File issues for findings (max 10)\n\n"
                    "Be thorough but avoid noise. Only file actionable findings."
                ),
            }
        ]

        self.agentic_loop(messages, self.get_tools())
