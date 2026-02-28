"""Base agent class — the foundation every agent role inherits from.

Every agent follows the same loop:
    1. Gather context (from GitHub, board, ticket history)
    2. Think (call Claude with role-specific system prompt + context)
    3. Act (execute tool calls — GitHub API, git, file ops)
    4. Report (post results, update board, hand off to next agent)
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

import anthropic

from agents.config import AgentRole, get_agent_config
from agents.context import TicketContext, build_handoff_block
from agents.github_ops import GitHubOps
from agents.state import TicketState, transition

logger = logging.getLogger("clawssistant.agents")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AGENT_SIGNATURE = "\n\n---\n*🤖 {role} Agent | Clawssistant Autonomous System*"
CONTEXT_BLOCK_START = "<!-- AGENT_CONTEXT_START -->"
CONTEXT_BLOCK_END = "<!-- AGENT_CONTEXT_END -->"
MAX_THINK_ITERATIONS = 10


@dataclass
class AgentAction:
    """A discrete action the agent wants to take."""

    tool: str
    params: dict[str, Any]
    reasoning: str = ""


@dataclass
class ActionResult:
    success: bool
    output: str = ""
    error: str = ""


@dataclass
class AgentMessage:
    role: str  # "orchestrator", "pm", "engineer", etc.
    content: str
    timestamp: float = field(default_factory=time.time)
    context: dict[str, Any] = field(default_factory=dict)


class Agent:
    """Base agent that wraps Claude API calls with GitHub context.

    Subclasses override:
        - `system_prompt` property for role-specific instructions
        - `get_tools()` for role-specific tool definitions
        - `handle_tool_call()` for role-specific tool execution
        - `run()` for the main agent loop
    """

    role: AgentRole = AgentRole.ORCHESTRATOR

    def __init__(self) -> None:
        self.config = get_agent_config(self.role)
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.github = GitHubOps(
            token=os.environ.get("GITHUB_TOKEN", ""),
            repo=os.environ.get("GITHUB_REPOSITORY", ""),
        )
        self.model = self.config.get("model", "claude-sonnet-4-6")
        self.max_tokens = self.config.get("max_tokens", 4096)

    # ------------------------------------------------------------------
    # Core prompt
    # ------------------------------------------------------------------

    @property
    def system_prompt(self) -> str:
        """Role-specific system prompt. Must be overridden by subclasses."""
        return self.config.get("system_prompt", "You are a helpful assistant.")

    @property
    def signature(self) -> str:
        return AGENT_SIGNATURE.format(role=self.role.value.title())

    # ------------------------------------------------------------------
    # Think — call Claude
    # ------------------------------------------------------------------

    def think(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> anthropic.types.Message:
        """Send context to Claude and get a response with optional tool use."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": self.system_prompt,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        logger.info("[%s] Thinking with %d messages...", self.role.value, len(messages))
        response = self.client.messages.create(**kwargs)
        logger.info(
            "[%s] Response: stop_reason=%s, content_blocks=%d",
            self.role.value,
            response.stop_reason,
            len(response.content),
        )
        return response

    # ------------------------------------------------------------------
    # Agentic loop — think + act repeatedly until done
    # ------------------------------------------------------------------

    def agentic_loop(
        self,
        initial_messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        """Run the think→act loop until Claude stops calling tools.

        Returns the final text response.
        """
        messages = list(initial_messages)
        final_text = ""

        for iteration in range(MAX_THINK_ITERATIONS):
            response = self.think(messages, tools)

            # Collect text and tool calls from the response
            text_parts: list[str] = []
            tool_calls: list[dict[str, Any]] = []

            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_calls.append(
                        {"id": block.id, "name": block.name, "input": block.input}
                    )

            if text_parts:
                final_text = "\n".join(text_parts)

            # If no tool calls, we're done
            if not tool_calls or response.stop_reason == "end_turn":
                break

            # Execute tool calls and build tool results
            assistant_content: list[dict[str, Any]] = []
            for block in response.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append(
                        {
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        }
                    )

            messages.append({"role": "assistant", "content": assistant_content})

            tool_results: list[dict[str, Any]] = []
            for tc in tool_calls:
                result = self.handle_tool_call(tc["name"], tc["input"])
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tc["id"],
                        "content": json.dumps(result) if isinstance(result, dict) else str(result),
                    }
                )

            messages.append({"role": "user", "content": tool_results})

        return final_text

    # ------------------------------------------------------------------
    # Tool handling — override in subclasses
    # ------------------------------------------------------------------

    def get_tools(self) -> list[dict[str, Any]]:
        """Return tool definitions available to this agent."""
        return self._common_tools()

    def handle_tool_call(self, name: str, params: dict[str, Any]) -> Any:
        """Execute a tool call. Override to add role-specific tools."""
        return self._handle_common_tool(name, params)

    # ------------------------------------------------------------------
    # Common tools available to all agents
    # ------------------------------------------------------------------

    def _common_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "comment_on_issue",
                "description": "Post a comment on a GitHub issue or PR.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "issue_number": {"type": "integer", "description": "Issue or PR number"},
                        "body": {"type": "string", "description": "Comment body (markdown)"},
                    },
                    "required": ["issue_number", "body"],
                },
            },
            {
                "name": "add_labels",
                "description": "Add labels to a GitHub issue.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "issue_number": {"type": "integer"},
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Labels to add",
                        },
                    },
                    "required": ["issue_number", "labels"],
                },
            },
            {
                "name": "remove_labels",
                "description": "Remove labels from a GitHub issue.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "issue_number": {"type": "integer"},
                        "labels": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["issue_number", "labels"],
                },
            },
            {
                "name": "get_issue",
                "description": "Get details of a GitHub issue including comments.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "issue_number": {"type": "integer"},
                    },
                    "required": ["issue_number"],
                },
            },
            {
                "name": "list_issues",
                "description": "List issues with optional label/state filter.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "labels": {"type": "string", "description": "Comma-separated labels"},
                        "state": {
                            "type": "string",
                            "enum": ["open", "closed", "all"],
                            "description": "Issue state filter",
                        },
                    },
                },
            },
            {
                "name": "update_ticket_state",
                "description": "Transition a ticket to a new state by updating labels.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "issue_number": {"type": "integer"},
                        "new_state": {
                            "type": "string",
                            "description": "Target state (e.g. 'in-progress', 'code-review')",
                        },
                    },
                    "required": ["issue_number", "new_state"],
                },
            },
            {
                "name": "create_issue",
                "description": "Create a new GitHub issue.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                        "labels": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["title", "body"],
                },
            },
            {
                "name": "close_issue",
                "description": "Close a GitHub issue.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "issue_number": {"type": "integer"},
                        "reason": {
                            "type": "string",
                            "enum": ["completed", "not_planned"],
                        },
                    },
                    "required": ["issue_number"],
                },
            },
        ]

    def _handle_common_tool(self, name: str, params: dict[str, Any]) -> Any:
        match name:
            case "comment_on_issue":
                body = params["body"] + self.signature
                return self.github.comment_on_issue(params["issue_number"], body)
            case "add_labels":
                return self.github.add_labels(params["issue_number"], params["labels"])
            case "remove_labels":
                return self.github.remove_labels(params["issue_number"], params["labels"])
            case "get_issue":
                return self.github.get_issue(params["issue_number"])
            case "list_issues":
                return self.github.list_issues(
                    labels=params.get("labels"), state=params.get("state", "open")
                )
            case "update_ticket_state":
                new_state = TicketState(params["new_state"])
                return self._transition_ticket(params["issue_number"], new_state)
            case "create_issue":
                return self.github.create_issue(
                    title=params["title"],
                    body=params["body"],
                    labels=params.get("labels", []),
                )
            case "close_issue":
                return self.github.close_issue(
                    params["issue_number"], reason=params.get("reason", "completed")
                )
            case _:
                return {"error": f"Unknown tool: {name}"}

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def _transition_ticket(self, issue_number: int, new_state: TicketState) -> dict[str, Any]:
        """Transition a ticket to a new state, updating labels."""
        issue = self.github.get_issue(issue_number)
        current_labels = [l["name"] for l in issue.get("labels", [])]

        # Find current state from labels
        current_state = None
        for label in current_labels:
            if label.startswith("state:"):
                try:
                    current_state = TicketState(label.removeprefix("state:"))
                except ValueError:
                    pass

        if current_state and not transition(current_state, new_state):
            return {
                "error": f"Invalid transition: {current_state.value} -> {new_state.value}"
            }

        # Remove old state label, add new one
        old_state_labels = [l for l in current_labels if l.startswith("state:")]
        if old_state_labels:
            self.github.remove_labels(issue_number, old_state_labels)
        self.github.add_labels(issue_number, [f"state:{new_state.value}"])

        return {"success": True, "new_state": new_state.value}

    # ------------------------------------------------------------------
    # Context preservation
    # ------------------------------------------------------------------

    def post_context(self, issue_number: int, context: TicketContext) -> None:
        """Post structured context block to an issue for handoff."""
        block = build_handoff_block(context, self.role.value)
        self.github.comment_on_issue(issue_number, block)

    def read_context(self, issue_number: int) -> TicketContext | None:
        """Read the latest context block from an issue."""
        issue = self.github.get_issue(issue_number)
        comments = issue.get("comments_data", [])

        for comment in reversed(comments):
            body = comment.get("body", "")
            if CONTEXT_BLOCK_START in body and CONTEXT_BLOCK_END in body:
                json_str = body.split(CONTEXT_BLOCK_START)[1].split(CONTEXT_BLOCK_END)[0].strip()
                try:
                    data = json.loads(json_str)
                    return TicketContext.from_dict(data)
                except (json.JSONDecodeError, KeyError):
                    continue
        return None

    # ------------------------------------------------------------------
    # Entrypoint — override in subclasses
    # ------------------------------------------------------------------

    def run(self, trigger: dict[str, Any]) -> None:
        """Main entrypoint. Subclasses implement their specific workflow."""
        raise NotImplementedError(f"{self.__class__.__name__} must implement run()")
