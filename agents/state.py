"""Ticket state machine — defines valid states and transitions.

Every ticket moves through a defined lifecycle. Invalid transitions are
rejected, ensuring tickets follow the review/security/QA pipeline.
"""

from __future__ import annotations

from enum import Enum


class TicketState(Enum):
    NEW = "new"
    TRIAGING = "triaging"
    FEASIBILITY_REVIEW = "feasibility-review"
    SCOPED = "scoped"
    BACKLOG = "backlog"
    READY = "ready"
    IN_PROGRESS = "in-progress"
    CODE_REVIEW = "code-review"
    SECURITY_REVIEW = "security-review"
    QA = "qa"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    BLOCKED = "blocked"
    ARCHIVED = "archived"


# Valid state transitions
TRANSITIONS: dict[TicketState, list[TicketState]] = {
    TicketState.NEW: [TicketState.TRIAGING],
    TicketState.TRIAGING: [TicketState.FEASIBILITY_REVIEW, TicketState.ARCHIVED],
    TicketState.FEASIBILITY_REVIEW: [TicketState.SCOPED, TicketState.ARCHIVED],
    TicketState.SCOPED: [TicketState.BACKLOG],
    TicketState.BACKLOG: [TicketState.READY, TicketState.ARCHIVED],
    TicketState.READY: [TicketState.IN_PROGRESS],
    TicketState.IN_PROGRESS: [
        TicketState.CODE_REVIEW,
        TicketState.BLOCKED,
        TicketState.ARCHIVED,
    ],
    TicketState.BLOCKED: [TicketState.IN_PROGRESS, TicketState.ARCHIVED],
    TicketState.CODE_REVIEW: [
        TicketState.SECURITY_REVIEW,
        TicketState.IN_PROGRESS,  # changes requested → back to engineer
    ],
    TicketState.SECURITY_REVIEW: [
        TicketState.QA,
        TicketState.IN_PROGRESS,  # security rejected → back to engineer
    ],
    TicketState.QA: [
        TicketState.DEPLOYING,
        TicketState.IN_PROGRESS,  # QA failed → back to engineer
    ],
    TicketState.DEPLOYING: [TicketState.DEPLOYED],
    TicketState.DEPLOYED: [TicketState.ARCHIVED],
    TicketState.ARCHIVED: [],  # terminal state
}


def transition(current: TicketState, target: TicketState) -> bool:
    """Check if a transition from current to target is valid."""
    return target in TRANSITIONS.get(current, [])


def get_valid_transitions(current: TicketState) -> list[TicketState]:
    """Get all valid next states from the current state."""
    return TRANSITIONS.get(current, [])


def is_terminal(state: TicketState) -> bool:
    """Check if a state is terminal (no further transitions)."""
    return len(TRANSITIONS.get(state, [])) == 0


def requires_security_review(state: TicketState) -> bool:
    """Check if the current state requires security review before advancing."""
    return state == TicketState.CODE_REVIEW


# ---------------------------------------------------------------------------
# Label scheme — maps states to GitHub label names and colors
# ---------------------------------------------------------------------------

STATE_LABELS: dict[TicketState, dict[str, str]] = {
    TicketState.NEW:                {"name": "state:new",               "color": "e6e6e6"},
    TicketState.TRIAGING:           {"name": "state:triaging",          "color": "fbca04"},
    TicketState.FEASIBILITY_REVIEW: {"name": "state:feasibility-review","color": "f9d0c4"},
    TicketState.SCOPED:             {"name": "state:scoped",            "color": "c2e0c6"},
    TicketState.BACKLOG:            {"name": "state:backlog",           "color": "bfdadc"},
    TicketState.READY:              {"name": "state:ready",             "color": "0e8a16"},
    TicketState.IN_PROGRESS:        {"name": "state:in-progress",       "color": "1d76db"},
    TicketState.CODE_REVIEW:        {"name": "state:code-review",       "color": "5319e7"},
    TicketState.SECURITY_REVIEW:    {"name": "state:security-review",   "color": "d93f0b"},
    TicketState.QA:                 {"name": "state:qa",                "color": "0075ca"},
    TicketState.DEPLOYING:          {"name": "state:deploying",         "color": "006b75"},
    TicketState.DEPLOYED:           {"name": "state:deployed",          "color": "0e8a16"},
    TicketState.BLOCKED:            {"name": "state:blocked",           "color": "b60205"},
    TicketState.ARCHIVED:           {"name": "state:archived",          "color": "808080"},
}

# Priority labels
PRIORITY_LABELS: dict[str, dict[str, str]] = {
    "P0": {"name": "priority:P0-critical", "color": "b60205"},
    "P1": {"name": "priority:P1-high",     "color": "d93f0b"},
    "P2": {"name": "priority:P2-medium",   "color": "fbca04"},
    "P3": {"name": "priority:P3-low",      "color": "0e8a16"},
    "P4": {"name": "priority:P4-backlog",  "color": "c2e0c6"},
}

# Type labels
TYPE_LABELS: dict[str, dict[str, str]] = {
    "epic":       {"name": "type:epic",       "color": "3e4b9e"},
    "feature":    {"name": "type:feature",    "color": "1d76db"},
    "user-story": {"name": "type:user-story", "color": "0075ca"},
    "bug":        {"name": "type:bug",        "color": "d73a4a"},
    "chore":      {"name": "type:chore",      "color": "e6e6e6"},
    "security":   {"name": "type:security",   "color": "d93f0b"},
    "tech-debt":  {"name": "type:tech-debt",  "color": "fbca04"},
}

# Agent assignment labels
AGENT_LABELS: dict[str, dict[str, str]] = {
    "engineer":    {"name": "agent:engineer",    "color": "1d76db"},
    "sr-engineer": {"name": "agent:sr-engineer", "color": "5319e7"},
    "security":    {"name": "agent:security",    "color": "d93f0b"},
    "infosec":     {"name": "agent:infosec",     "color": "b60205"},
    "qa":          {"name": "agent:qa",          "color": "0075ca"},
    "pm":          {"name": "agent:pm",          "color": "006b75"},
}


def get_all_labels() -> dict[str, str]:
    """Get all labels that need to exist in the repo. Returns {name: color}."""
    all_labels: dict[str, str] = {}
    for label_set in [STATE_LABELS, PRIORITY_LABELS, TYPE_LABELS, AGENT_LABELS]:
        for info in label_set.values():
            all_labels[info["name"]] = info["color"]
    return all_labels
