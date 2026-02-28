"""Security & InfoSec Agents — pair-program security review before deployment.

Two agents work in tandem on every security review:
- Security Engineer: code-level vulnerability scanning (OWASP top 10,
  dependency issues, auth flaws, injection, path traversal)
- InfoSec Agent: threat modeling, compliance, trust boundaries, data flow

BOTH must approve before deployment proceeds. Either can block.
"""

from __future__ import annotations

import logging
from typing import Any

from agents.base import Agent
from agents.config import AgentRole
from agents.context import SecurityReviewEntry

logger = logging.getLogger("clawssistant.agents.security")


class SecurityAgent(Agent):
    """Security Engineer — code-level vulnerability scanning."""

    role = AgentRole.SECURITY

    @property
    def system_prompt(self) -> str:
        return """You are the Security Engineer Agent for the Clawssistant project — an autonomous,
open-source, Claude-powered home assistant that controls physical devices in homes.

## Your Role
You are the SECURITY GATE. No code deploys without your approval. You pair-program
every review with the InfoSec agent. Your focus is CODE-LEVEL security.

## What You Scan For

### OWASP Top 10 (adapted for this project)
1. **Injection** — SQL injection in SQLite queries, command injection in subprocess
   calls, template injection in TTS/voice responses
2. **Broken Auth** — API token validation, speaker verification bypass, PIN handling
3. **Sensitive Data Exposure** — API keys in logs, credentials in config, audio data leaks
4. **XXE/XML** — if any XML parsing exists
5. **Broken Access Control** — skill sandbox escapes, unauthorized device actions,
   privilege escalation via voice commands
6. **Security Misconfiguration** — debug mode in prod, open ports, permissive CORS,
   default credentials
7. **XSS** — in web dashboard, API responses rendered in browsers
8. **Insecure Deserialization** — pickle, yaml.load (vs safe_load), JSON parsing
9. **Known Vulnerabilities** — outdated dependencies, CVEs
10. **Insufficient Logging** — security events not logged, audit trail gaps

### Project-Specific Concerns
- **Path traversal** in skill loading, file read/write operations
- **Voice command injection** — can a TV/speaker trigger dangerous actions?
- **MCP server isolation** — can a malicious MCP server escape its sandbox?
- **Home Assistant token exposure** — is the HA token properly protected?
- **Audio buffer handling** — are audio buffers cleared from memory?
- **Trust boundary violations** — does untrusted input cross into trusted zones?

## Review Output Format
```
## 🔒 Security Review

### Scan Summary
**Verdict:** [APPROVED / BLOCKED / CONDITIONALLY APPROVED]
**Severity:** [none / low / medium / high / critical]

### Findings
#### Critical (must fix)
- [finding with file:line reference]

#### High
- [finding]

#### Medium
- [finding]

#### Low / Informational
- [finding]

### Dependency Check
- [any known CVEs in dependencies]

### Trust Boundary Analysis
- [any violations of the trust model in CLAUDE.md]

### Recommendations
- [security improvements beyond the current PR]
```

## Decision Rules
- **APPROVE**: No critical/high findings, all medium findings are acknowledged
- **BLOCK**: Any critical finding, or 2+ high findings
- **CONDITIONALLY APPROVE**: 1 high finding that can be addressed in a follow-up

## Safety Parameters
- When in doubt, BLOCK. Security is more important than velocity.
- Always check subprocess calls for shell=True
- Always check file operations for path traversal
- Always check that eval/exec are not used
- Flag any hardcoded credentials, even test ones in non-test files
"""

    def get_tools(self) -> list[dict[str, Any]]:
        tools = self._common_tools()
        tools.extend([
            {
                "name": "get_pr_diff",
                "description": "Get the full diff of a PR for security review.",
                "input_schema": {
                    "type": "object",
                    "properties": {"pr_number": {"type": "integer"}},
                    "required": ["pr_number"],
                },
            },
            {
                "name": "submit_security_review",
                "description": "Submit the security review verdict.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pr_number": {"type": "integer"},
                        "issue_number": {"type": "integer"},
                        "verdict": {
                            "type": "string",
                            "enum": ["approved", "blocked", "conditionally_approved"],
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["none", "low", "medium", "high", "critical"],
                        },
                        "findings": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "review_body": {"type": "string"},
                    },
                    "required": ["pr_number", "issue_number", "verdict", "review_body"],
                },
            },
        ])
        return tools

    def handle_tool_call(self, name: str, params: dict[str, Any]) -> Any:
        match name:
            case "get_pr_diff":
                diff = self.github.get_pr_diff(params["pr_number"])
                return diff[:25000] if len(diff) > 25000 else diff
            case "submit_security_review":
                return self._submit_review(params)
            case _:
                return self._handle_common_tool(name, params)

    def _submit_review(self, params: dict[str, Any]) -> dict[str, Any]:
        """Submit security review and update ticket state."""
        pr_number = params["pr_number"]
        issue_number = params["issue_number"]
        verdict = params["verdict"]
        body = params["review_body"] + self.signature

        # Post review on PR
        event = "approve" if verdict == "approved" else "request-changes"
        self.github.review_pr(pr_number, event, body)

        # Save security review to context
        context = self.read_context(issue_number)
        if context:
            entry = SecurityReviewEntry(
                reviewer_role="security",
                verdict=verdict,
                findings=params.get("findings", []),
                severity=params.get("severity", "none"),
                details=params["review_body"],
            )
            context.add_security_review(entry)
            self.post_context(issue_number, context)

        # Update labels
        if verdict == "blocked":
            from agents.state import TicketState
            self._transition_ticket(issue_number, TicketState.IN_PROGRESS)
            self.github.add_labels(issue_number, ["security:blocked"])

        return {"success": True, "verdict": verdict}

    def run(self, trigger: dict[str, Any]) -> None:
        pr_number = int(trigger.get("pr_number", 0))
        issue_number = int(trigger.get("issue_number", 0))

        if not pr_number:
            logger.warning("Security agent called without pr_number")
            return

        pr = self.github.get_pr(pr_number)
        diff = self.github.get_pr_diff(pr_number)
        diff_preview = diff[:20000] if len(diff) > 20000 else diff

        messages = [
            {
                "role": "user",
                "content": (
                    f"Perform a SECURITY REVIEW of this PR.\n\n"
                    f"**PR #{pr_number}:** {pr.get('title', 'N/A')}\n"
                    f"**Changes:** +{pr.get('additions', 0)} -{pr.get('deletions', 0)}\n\n"
                    f"**Diff:**\n```diff\n{diff_preview}\n```\n\n"
                    f"Scan for ALL security concerns. Use submit_security_review when done.\n"
                    f"Issue number for context: {issue_number}"
                ),
            }
        ]

        self.agentic_loop(messages, self.get_tools())


class InfoSecAgent(Agent):
    """InfoSec Agent — threat modeling and compliance review."""

    role = AgentRole.INFOSEC

    @property
    def system_prompt(self) -> str:
        return """You are the Information Security (InfoSec) Agent for the Clawssistant project —
an autonomous, open-source, Claude-powered home assistant controlling physical devices.

## Your Role
You pair-program security reviews with the Security Engineer. Your focus is
THREAT MODELING, COMPLIANCE, and SYSTEMIC security — the big picture.

## What You Evaluate

### Threat Model (from CLAUDE.md Security Architecture)
Trust boundaries:
- Internet → Firewall + TLS → API Server
- Audio environment → Wake Word + Speaker ID → Voice Pipeline
- Community skills → Subprocess sandbox → Core Runtime
- MCP tool results → Input validation → Claude Brain
- Companion apps → Token auth + rate limit → Conversation Manager

For each PR, ask: "Does this change cross or weaken any trust boundary?"

### Data Flow Analysis
- Where does user data flow? Is it protected at every hop?
- Are there new data paths that bypass existing controls?
- Is sensitive data (audio, tokens, personal info) handled correctly?

### Compliance & Privacy
- GDPR/privacy: is personal data minimized? Can it be deleted?
- No telemetry/phone-home: does this change add any external calls?
- Audio handling: are buffers cleared? Is nothing persisted without consent?

### Attack Surface
- Does this PR increase the attack surface?
- New network endpoints?
- New file system access?
- New subprocess calls?
- New external dependencies?

### Defense in Depth
- Are there multiple layers of protection?
- What happens if one control fails?
- Is the principle of least privilege followed?

## Review Output Format
```
## 🛡️ InfoSec Review

### Verdict: [APPROVED / BLOCKED / CONDITIONALLY APPROVED]
### Severity: [none / low / medium / high / critical]

### Threat Model Impact
- Trust boundaries affected: [list]
- New attack surface: [description]

### Data Flow
- Sensitive data paths: [analysis]
- Privacy implications: [analysis]

### Findings
- [finding with severity and recommendation]

### Risk Assessment
[Overall risk evaluation]
```

## Decision Rules
- APPROVE: No trust boundary violations, acceptable risk
- BLOCK: Trust boundary weakened, new unprotected attack surface, privacy violation
- CONDITIONALLY APPROVE: Minor concerns that can be tracked

## Safety Parameters
- Physical device safety is paramount — blocking a bad change to a lock/alarm
  is ALWAYS worth the delay
- Privacy violations are always critical findings
- Any new external network call is suspicious until justified
"""

    def get_tools(self) -> list[dict[str, Any]]:
        tools = self._common_tools()
        tools.extend([
            {
                "name": "get_pr_diff",
                "description": "Get the full diff of a PR for infosec review.",
                "input_schema": {
                    "type": "object",
                    "properties": {"pr_number": {"type": "integer"}},
                    "required": ["pr_number"],
                },
            },
            {
                "name": "submit_infosec_review",
                "description": "Submit the infosec review verdict.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pr_number": {"type": "integer"},
                        "issue_number": {"type": "integer"},
                        "verdict": {
                            "type": "string",
                            "enum": ["approved", "blocked", "conditionally_approved"],
                        },
                        "severity": {"type": "string"},
                        "findings": {"type": "array", "items": {"type": "string"}},
                        "review_body": {"type": "string"},
                    },
                    "required": ["pr_number", "issue_number", "verdict", "review_body"],
                },
            },
        ])
        return tools

    def handle_tool_call(self, name: str, params: dict[str, Any]) -> Any:
        match name:
            case "get_pr_diff":
                diff = self.github.get_pr_diff(params["pr_number"])
                return diff[:25000] if len(diff) > 25000 else diff
            case "submit_infosec_review":
                return self._submit_review(params)
            case _:
                return self._handle_common_tool(name, params)

    def _submit_review(self, params: dict[str, Any]) -> dict[str, Any]:
        pr_number = params["pr_number"]
        issue_number = params["issue_number"]
        verdict = params["verdict"]
        body = params["review_body"] + self.signature

        event = "approve" if verdict == "approved" else "request-changes"
        self.github.review_pr(pr_number, event, body)

        # Update context
        context = self.read_context(issue_number)
        if context:
            entry = SecurityReviewEntry(
                reviewer_role="infosec",
                verdict=verdict,
                findings=params.get("findings", []),
                severity=params.get("severity", "none"),
                details=params["review_body"],
            )
            context.add_security_review(entry)

            # Check if both security AND infosec have approved → move to QA
            if context.security_approved():
                from agents.state import TicketState
                self._transition_ticket(issue_number, TicketState.QA)
                self.github.remove_labels(issue_number, ["security:blocked"])

            self.post_context(issue_number, context)

        if verdict == "blocked":
            from agents.state import TicketState
            self._transition_ticket(issue_number, TicketState.IN_PROGRESS)
            self.github.add_labels(issue_number, ["security:blocked"])

        return {"success": True, "verdict": verdict}

    def run(self, trigger: dict[str, Any]) -> None:
        pr_number = int(trigger.get("pr_number", 0))
        issue_number = int(trigger.get("issue_number", 0))

        if not pr_number:
            logger.warning("InfoSec agent called without pr_number")
            return

        pr = self.github.get_pr(pr_number)
        diff = self.github.get_pr_diff(pr_number)
        diff_preview = diff[:20000] if len(diff) > 20000 else diff

        messages = [
            {
                "role": "user",
                "content": (
                    f"Perform an INFOSEC REVIEW of this PR from a threat modeling and "
                    f"compliance perspective.\n\n"
                    f"**PR #{pr_number}:** {pr.get('title', 'N/A')}\n"
                    f"**Changes:** +{pr.get('additions', 0)} -{pr.get('deletions', 0)}\n\n"
                    f"**Diff:**\n```diff\n{diff_preview}\n```\n\n"
                    f"Focus on trust boundaries, data flow, privacy, and attack surface.\n"
                    f"Use submit_infosec_review when done. Issue: {issue_number}"
                ),
            }
        ]

        self.agentic_loop(messages, self.get_tools())
