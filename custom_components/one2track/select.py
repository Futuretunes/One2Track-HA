"""Select platform for One2Track GPS."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import One2TrackConfigEntry
from .const import CMD_GPS_INTERVALS, CMD_PROFILE_MODE, GPS_INTERVAL_OPTIONS
from .coordinator import One2TrackCoordinator
from .entity import One2TrackEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: One2TrackConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up One2Track select entities."""
    coordinator = entry.runtime_data

    entities: list[SelectEntity] = []
    for uuid in coordinator.data:
        caps = coordinator.device_capabilities.get(uuid, [])

        gps_cmd = next((c for c in caps if c in CMD_GPS_INTERVALS), None)
        if gps_cmd:
            entities.append(One2TrackGpsIntervalSelect(coordinator, uuid, gps_cmd))

        if CMD_PROFILE_MODE in caps:
            entities.append(One2TrackProfileSelect(coordinator, uuid))

    async_add_entities(entities)


class One2TrackGpsIntervalSelect(One2TrackEntity, SelectEntity):
    """Select entity for GPS tracking interval."""

    _attr_translation_key = "gps_interval"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:timer-outline"

    def __init__(
        self, coordinator: One2TrackCoordinator, uuid: str, cmd_code: str,
    ) -> None:
        super().__init__(coordinator, uuid)
        self._cmd_code = cmd_code
        self._attr_unique_id = f"{uuid}_gps_interval"
        self._attr_options = list(GPS_INTERVAL_OPTIONS.values())
        self._label_to_value = {v: k for k, v in GPS_INTERVAL_OPTIONS.items()}

    @property
    def current_option(self) -> str | None:
        return None

    async def async_select_option(self, option: str) -> None:
        """Set the GPS tracking interval."""
        value = self._label_to_value.get(option)
        if value:
            await self.coordinator.api.send_command(
                self._uuid, self._cmd_code, [value]
            )


class One2TrackProfileSelect(One2TrackEntity, SelectEntity):
    """Select entity for profile/sound mode."""

    _attr_translation_key = "profile_mode"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:volume-high"
    _attr_options = ["Sound", "Vibrate", "Silent"]

    _MODE_VALUES = {"Sound": "1", "Vibrate": "2", "Silent": "3"}

    def __init__(self, coordinator: One2TrackCoordinator, uuid: str) -> None:
        super().__init__(coordinator, uuid)
        self._attr_unique_id = f"{uuid}_profile_mode"

    @property
    def current_option(self) -> str | None:
        return None

    async def async_select_option(self, option: str) -> None:
        """Set the profile mode."""
        value = self._MODE_VALUES.get(option)
        if value:
            await self.coordinator.api.send_command(
                self._uuid, CMD_PROFILE_MODE, [value]
            )
