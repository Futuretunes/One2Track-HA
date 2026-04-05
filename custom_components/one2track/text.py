"""Text platform for One2Track GPS — SOS number configuration."""

from __future__ import annotations

import re

from homeassistant.components.text import TextEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import One2TrackConfigEntry
from .const import CMD_SET_SOS_NUMBER
from .coordinator import One2TrackCoordinator
from .entity import One2TrackEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: One2TrackConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up One2Track text entities."""
    coordinator = entry.runtime_data

    entities: list[TextEntity] = []
    for uuid in coordinator.data:
        caps = coordinator.device_capabilities.get(uuid, [])
        if not caps or CMD_SET_SOS_NUMBER in caps:
            entities.append(One2TrackSosNumber(coordinator, uuid))

    async_add_entities(entities)


class One2TrackSosNumber(One2TrackEntity, TextEntity):
    """Text entity for configuring the SOS number."""

    _attr_translation_key = "sos_number"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:phone-alert"
    _attr_pattern = r"^\+?[0-9\s\-]{0,20}$"
    _attr_native_max = 20

    def __init__(self, coordinator: One2TrackCoordinator, uuid: str) -> None:
        super().__init__(coordinator, uuid)
        self._attr_unique_id = f"{uuid}_sos_number"
        self._current_value: str | None = None

    @property
    def native_value(self) -> str | None:
        return self._current_value

    async def async_set_value(self, value: str) -> None:
        """Set the SOS number on the watch."""
        # Clean up the number
        cleaned = re.sub(r"[^\d+]", "", value)
        if cleaned:
            await self.coordinator.api.send_command(
                self._uuid, CMD_SET_SOS_NUMBER, [cleaned]
            )
            self._current_value = cleaned
            self.async_write_ha_state()
