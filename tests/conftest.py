"""Root conftest — shared fixtures for all Clawssistant tests."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to the test fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def tmp_config(tmp_path: Path) -> Path:
    """Create a minimal config.yaml in a temp directory and return its path."""
    config = {
        "assistant": {"name": "TestAssistant", "wake_word": "clawssistant", "language": "en-US"},
        "claude": {"api_key": "test-api-key-not-real", "model": "claude-sonnet-4-6", "max_tokens": 256},
        "homeassistant": {
            "url": "http://localhost:8123",
            "token": "test-ha-token-not-real",
            "verify_ssl": False,
        },
        "conversation": {"max_history": 5, "timeout_seconds": 60},
        "api": {
            "host": "127.0.0.1",
            "port": 0,  # OS picks a free port
            "auth": {"enabled": False},  # disabled for testing
        },
        "logging": {"level": "debug"},
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(config))
    return config_path


# ---------------------------------------------------------------------------
# Mock: Anthropic / Claude
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_anthropic_client() -> MagicMock:
    """A mocked anthropic.AsyncAnthropic client.

    Usage in tests:
        async def test_brain(mock_anthropic_client):
            mock_anthropic_client.messages.create.return_value = MessageMock(...)
    """
    client = MagicMock()
    client.messages = MagicMock()
    client.messages.create = AsyncMock(
        return_value=_make_claude_response("Hello! How can I help?")
    )
    return client


def _make_claude_response(text: str, tool_calls: list[dict[str, Any]] | None = None) -> MagicMock:
    """Build a mock Claude API response."""
    response = MagicMock()
    response.id = "msg_test_123"
    response.model = "claude-sonnet-4-6"
    response.stop_reason = "end_turn"
    response.usage = MagicMock(input_tokens=10, output_tokens=20)

    content_blocks = []

    if text:
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = text
        content_blocks.append(text_block)

    if tool_calls:
        for tc in tool_calls:
            tool_block = MagicMock()
            tool_block.type = "tool_use"
            tool_block.id = tc.get("id", "toolu_test_1")
            tool_block.name = tc["name"]
            tool_block.input = tc.get("input", {})
            content_blocks.append(tool_block)

    response.content = content_blocks
    return response


@pytest.fixture
def make_claude_response():
    """Factory fixture for building mock Claude responses."""
    return _make_claude_response


# ---------------------------------------------------------------------------
# Mock: Home Assistant
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_ha_states() -> list[dict[str, Any]]:
    """Sample Home Assistant entity states for testing."""
    return [
        {
            "entity_id": "light.living_room",
            "state": "on",
            "attributes": {"brightness": 200, "color_temp": 370, "friendly_name": "Living Room Light"},
        },
        {
            "entity_id": "light.bedroom",
            "state": "off",
            "attributes": {"friendly_name": "Bedroom Light"},
        },
        {
            "entity_id": "climate.thermostat",
            "state": "heat",
            "attributes": {
                "temperature": 72,
                "current_temperature": 68,
                "friendly_name": "Main Thermostat",
            },
        },
        {
            "entity_id": "lock.front_door",
            "state": "locked",
            "attributes": {"friendly_name": "Front Door Lock"},
        },
        {
            "entity_id": "sensor.outdoor_temp",
            "state": "45.2",
            "attributes": {"unit_of_measurement": "°F", "friendly_name": "Outdoor Temperature"},
        },
    ]


@pytest.fixture
def mock_ha_client(mock_ha_states: list[dict[str, Any]]) -> MagicMock:
    """A mocked Home Assistant REST client."""
    client = MagicMock()
    client.get_states = AsyncMock(return_value=mock_ha_states)
    client.get_state = AsyncMock(
        side_effect=lambda eid: next((s for s in mock_ha_states if s["entity_id"] == eid), None)
    )
    client.call_service = AsyncMock(return_value={"result": "ok"})
    client.is_connected = MagicMock(return_value=True)
    return client


# ---------------------------------------------------------------------------
# Mock: Voice Pipeline
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_stt() -> AsyncMock:
    """A mocked speech-to-text engine that returns a fixed transcription."""
    stt = AsyncMock()
    stt.transcribe = AsyncMock(return_value="turn on the living room lights")
    return stt


@pytest.fixture
def mock_tts() -> AsyncMock:
    """A mocked text-to-speech engine that returns fake audio bytes."""
    tts = AsyncMock()
    tts.synthesize = AsyncMock(return_value=b"\x00" * 1024)  # silent audio
    return tts


@pytest.fixture
def mock_wake_word() -> AsyncMock:
    """A mocked wake word detector."""
    detector = AsyncMock()
    detector.detected = AsyncMock(return_value=True)
    return detector


# ---------------------------------------------------------------------------
# Mock: Audio
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_audio_bytes() -> bytes:
    """16kHz 16-bit mono PCM silence — 1 second."""
    return b"\x00\x00" * 16000


@pytest.fixture
def sample_audio_path(tmp_path: Path, sample_audio_bytes: bytes) -> Path:
    """Write sample audio to a temp .wav file."""
    import struct
    import wave

    wav_path = tmp_path / "test.wav"
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(sample_audio_bytes)
    return wav_path


# ---------------------------------------------------------------------------
# Mock: MQTT
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_mqtt_client() -> MagicMock:
    """A mocked MQTT client."""
    client = MagicMock()
    client.publish = AsyncMock()
    client.subscribe = AsyncMock()
    client.messages = AsyncMock()  # async context manager for message iteration
    return client


# ---------------------------------------------------------------------------
# Mock: Database / Memory
# ---------------------------------------------------------------------------


@pytest.fixture
async def memory_db(tmp_path: Path) -> AsyncGenerator[Path, None]:
    """Create a temporary SQLite database for memory/conversation tests."""
    db_path = tmp_path / "test_memory.db"
    # The actual schema creation would be done by the memory module.
    # This just provides the path.
    yield db_path
    # Cleanup is handled by tmp_path


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def env_with_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set environment variables that the config loader expects."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-sk-not-real")
    monkeypatch.setenv("HA_TOKEN", "test-ha-token-not-real")
    monkeypatch.setenv("CLAWSSISTANT_API_KEY", "test-api-key-not-real")
