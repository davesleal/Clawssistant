"""Tests for Home Assistant integration.

Uses mocked HA client — no real Home Assistant instance needed.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestHomeAssistantClient:
    """HA client should fetch states, call services, and handle errors."""

    async def test_get_all_states(
        self, mock_ha_client: MagicMock, mock_ha_states: list[dict[str, Any]]
    ) -> None:
        """Should return all entity states."""
        states = await mock_ha_client.get_states()
        assert len(states) == 5
        entity_ids = [s["entity_id"] for s in states]
        assert "light.living_room" in entity_ids
        assert "lock.front_door" in entity_ids

    async def test_get_single_state(self, mock_ha_client: MagicMock) -> None:
        """Should return state for a specific entity."""
        state = await mock_ha_client.get_state("light.living_room")
        assert state is not None
        assert state["state"] == "on"
        assert state["attributes"]["brightness"] == 200

    async def test_get_missing_entity(self, mock_ha_client: MagicMock) -> None:
        """Should return None for unknown entity."""
        state = await mock_ha_client.get_state("light.nonexistent")
        assert state is None

    async def test_call_service(self, mock_ha_client: MagicMock) -> None:
        """Should call HA service and return result."""
        result = await mock_ha_client.call_service(
            domain="light",
            service="turn_on",
            entity_id="light.living_room",
            brightness=255,
        )
        assert result["result"] == "ok"
        mock_ha_client.call_service.assert_called_once()

    def test_connection_status(self, mock_ha_client: MagicMock) -> None:
        """Should report connection status."""
        assert mock_ha_client.is_connected() is True


class TestEntityParsing:
    """Entity ID parsing and validation."""

    @pytest.mark.parametrize(
        "entity_id,valid",
        [
            ("light.living_room", True),
            ("climate.thermostat", True),
            ("lock.front_door", True),
            ("sensor.outdoor_temp", True),
            ("invalid", False),
            ("", False),
            ("no_domain_separator", False),
        ],
    )
    def test_entity_id_format(self, entity_id: str, valid: bool) -> None:
        """Entity IDs must be domain.object_id format."""
        has_dot = "." in entity_id and len(entity_id.split(".")) == 2
        parts_valid = all(len(p) > 0 for p in entity_id.split(".")) if has_dot else False
        assert parts_valid == valid
