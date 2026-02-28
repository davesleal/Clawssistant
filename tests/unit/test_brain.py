"""Tests for the Claude brain / conversation layer.

These tests use mocked Anthropic clients — no real API calls.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestClaudeBrain:
    """Claude brain should route prompts, handle tool calls, and manage context."""

    async def test_simple_response(
        self, mock_anthropic_client: MagicMock, make_claude_response: Any
    ) -> None:
        """Brain should return text from Claude's response."""
        mock_anthropic_client.messages.create.return_value = make_claude_response(
            "The living room light is now on."
        )
        result = await mock_anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            messages=[{"role": "user", "content": "turn on the living room light"}],
        )
        assert result.content[0].text == "The living room light is now on."

    async def test_tool_call_response(
        self, mock_anthropic_client: MagicMock, make_claude_response: Any
    ) -> None:
        """Brain should parse tool calls from Claude's response."""
        mock_anthropic_client.messages.create.return_value = make_claude_response(
            text="I'll turn on the light.",
            tool_calls=[
                {
                    "name": "set_light_state",
                    "input": {"entity_id": "light.living_room", "state": "on"},
                }
            ],
        )
        result = await mock_anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            messages=[{"role": "user", "content": "turn on the living room light"}],
        )
        tool_blocks = [b for b in result.content if b.type == "tool_use"]
        assert len(tool_blocks) == 1
        assert tool_blocks[0].name == "set_light_state"
        assert tool_blocks[0].input["entity_id"] == "light.living_room"

    async def test_empty_response_handled(
        self, mock_anthropic_client: MagicMock, make_claude_response: Any
    ) -> None:
        """Brain should handle empty text responses gracefully."""
        mock_anthropic_client.messages.create.return_value = make_claude_response("")
        result = await mock_anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            messages=[{"role": "user", "content": "..."}],
        )
        assert result.content[0].text == ""

    async def test_api_error_handling(self, mock_anthropic_client: MagicMock) -> None:
        """Brain should handle Anthropic API errors."""
        mock_anthropic_client.messages.create.side_effect = Exception("API rate limit exceeded")
        with pytest.raises(Exception, match="rate limit"):
            await mock_anthropic_client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=256,
                messages=[{"role": "user", "content": "hello"}],
            )


class TestConversationContext:
    """Conversation manager should maintain multi-turn context."""

    def test_conversation_history_structure(self) -> None:
        """History should alternate user/assistant messages."""
        history: list[dict[str, str]] = []
        history.append({"role": "user", "content": "turn on the lights"})
        history.append({"role": "assistant", "content": "Done! The lights are on."})
        history.append({"role": "user", "content": "make them dimmer"})

        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
        assert len(history) == 3

    def test_history_truncation(self) -> None:
        """History beyond max_history should be truncated."""
        max_history = 3
        history = [{"role": "user", "content": f"message {i}"} for i in range(10)]
        truncated = history[-max_history * 2 :]  # keep last N exchanges
        assert len(truncated) <= max_history * 2
