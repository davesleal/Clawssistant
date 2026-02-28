"""Context preservation — ensures proper handoff between agents.

Every ticket carries a TicketContext that contains the full history of
decisions, reviews, and state transitions. When an agent finishes its work,
it serializes the context into a structured GitHub comment so the next agent
can pick up exactly where the previous one left off.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ReviewEntry:
    """A single code review record."""

    reviewer_role: str
    verdict: str  # "approved", "changes_requested", "commented"
    summary: str
    timestamp: float = field(default_factory=time.time)
    details: str = ""


@dataclass
class SecurityReviewEntry:
    """A security/infosec review record."""

    reviewer_role: str  # "security" or "infosec"
    verdict: str  # "approved", "blocked", "conditionally_approved"
    findings: list[str] = field(default_factory=list)
    severity: str = "none"  # "none", "low", "medium", "high", "critical"
    timestamp: float = field(default_factory=time.time)
    details: str = ""


@dataclass
class QAResult:
    """A QA test result."""

    verdict: str  # "passed", "failed", "partial"
    test_summary: str = ""
    failures: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentHandoff:
    """Record of a handoff between agents."""

    from_role: str
    to_role: str
    reason: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class TicketContext:
    """Full context for a ticket — the single source of truth for handoffs.

    This gets serialized into GitHub issue comments as structured JSON blocks
    so any agent can reconstruct the full picture.
    """

    # Identity
    ticket_id: int = 0
    title: str = ""
    description: str = ""

    # Classification
    ticket_type: str = ""  # "epic", "feature", "user-story", "bug", "chore"
    epic_ref: int | None = None  # parent epic issue number
    user_story: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)

    # Triage results
    feasibility_assessment: str = ""
    user_research_notes: str = ""
    scope_estimate: str = ""  # "XS", "S", "M", "L", "XL"
    priority: str = ""  # "P0-critical", "P1-high", "P2-medium", "P3-low", "P4-backlog"
    estimated_effort_hours: float = 0
    triage_decision: str = ""  # "accepted", "rejected", "needs-info"
    triage_reasoning: str = ""

    # Development
    assigned_engineer: str = ""
    branch_name: str = ""
    pr_number: int | None = None
    implementation_notes: str = ""
    blocked: bool = False
    block_reason: str = ""
    collaborating_agents: list[str] = field(default_factory=list)

    # Reviews
    reviews: list[dict[str, Any]] = field(default_factory=list)
    security_reviews: list[dict[str, Any]] = field(default_factory=list)
    qa_results: list[dict[str, Any]] = field(default_factory=list)

    # Lifecycle
    state: str = "new"
    state_history: list[dict[str, Any]] = field(default_factory=list)
    handoffs: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    # Archive
    archived: bool = False
    archive_reason: str = ""
    archive_context: str = ""
    archive_learnings: str = ""

    def to_dict(self) -> dict[str, Any]:
        self.updated_at = time.time()
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TicketContext:
        # Filter to known fields only
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    def add_state_transition(self, from_state: str, to_state: str, agent: str) -> None:
        self.state_history.append(
            {
                "from": from_state,
                "to": to_state,
                "agent": agent,
                "timestamp": time.time(),
            }
        )
        self.state = to_state
        self.updated_at = time.time()

    def add_handoff(self, from_role: str, to_role: str, reason: str) -> None:
        self.handoffs.append(
            {
                "from_role": from_role,
                "to_role": to_role,
                "reason": reason,
                "timestamp": time.time(),
            }
        )
        self.updated_at = time.time()

    def add_review(self, entry: ReviewEntry) -> None:
        self.reviews.append(asdict(entry))
        self.updated_at = time.time()

    def add_security_review(self, entry: SecurityReviewEntry) -> None:
        self.security_reviews.append(asdict(entry))
        self.updated_at = time.time()

    def add_qa_result(self, result: QAResult) -> None:
        self.qa_results.append(asdict(result))
        self.updated_at = time.time()

    def archive(self, reason: str, context: str, learnings: str) -> None:
        self.archived = True
        self.archive_reason = reason
        self.archive_context = context
        self.archive_learnings = learnings
        self.updated_at = time.time()

    def security_approved(self) -> bool:
        """Both security AND infosec must approve."""
        sec_approved = any(
            r.get("verdict") == "approved" and r.get("reviewer_role") == "security"
            for r in self.security_reviews
        )
        infosec_approved = any(
            r.get("verdict") == "approved" and r.get("reviewer_role") == "infosec"
            for r in self.security_reviews
        )
        return sec_approved and infosec_approved


def build_handoff_block(context: TicketContext, from_agent: str) -> str:
    """Build a structured comment block for context handoff."""
    context_json = json.dumps(context.to_dict(), indent=2)
    return (
        f"<!-- AGENT_CONTEXT_START -->\n"
        f"```json\n{context_json}\n```\n"
        f"<!-- AGENT_CONTEXT_END -->\n\n"
        f"*Context updated by `{from_agent}` agent at {time.strftime('%Y-%m-%d %H:%M UTC')}*"
    )
