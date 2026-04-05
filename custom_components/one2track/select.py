"""Select platform for One2Track GPS."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import One2TrackConfigEntry
from .const import CMD_GPS_INTERVALS, CMD_PROFILE_MODE, DOMAIN, GPS_INTERVAL_OPTIONS
from .coordinator import One2TrackCoordinator

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

        # GPS interval select — add if any GPS interval command is supported
        gps_cmd = next((c for c in caps if c in CMD_GPS_INTERVALS), None)
        if gps_cmd:
            entities.append(One2TrackGpsIntervalSelect(coordinator, uuid, gps_cmd))

        # Profile mode select — add if supported
        if CMD_PROFILE_MODE in caps:
            entities.append(One2TrackProfileSelect(coordinator, uuid))

    async_add_entities(entities)


class One2TrackGpsIntervalSelect(
    CoordinatorEntity[One2TrackCoordinator], SelectEntity
):
    """Select entity for GPS tracking interval."""

    _attr_has_entity_name = True
    _attr_translation_key = "gps_interval"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:timer-outline"

    def __init__(
        self, coordinator: One2TrackCoordinator, uuid: str, cmd_code: str,
    ) -> None:
        super().__init__(coordinator)
        self._uuid = uuid
        self._cmd_code = cmd_code
        self._attr_unique_id = f"{uuid}_gps_interval"
        self._attr_options = list(GPS_INTERVAL_OPTIONS.values())
        self._value_to_label = GPS_INTERVAL_OPTIONS
        self._label_to_value = {v: k for k, v in GPS_INTERVAL_OPTIONS.items()}

    @property
    def device_info(self) -> dict[str, Any]:
        data = self.coordinator.data.get(self._uuid, {})
        return {
            "identifiers": {(DOMAIN, self._uuid)},
            "name": data.get("name", f"One2Track {self._uuid[:8]}"),
            "manufacturer": "One2Track",
            "model": data.get("device_model_name", "GPS Watch"),
        }

    @property
    def current_option(self) -> str | None:
        # The API doesn't directly report the current interval in device data,
        # so we don't have a guaranteed way to read it back.
        return None

    async def async_select_option(self, option: str) -> None:
        """Set the GPS tracking interval."""
        value = self._label_to_value.get(option)
        if value:
            await self.coordinator.api.send_command(
                self._uuid, self._cmd_code, [value]
            )


class One2TrackProfileSelect(
    CoordinatorEntity[One2TrackCoordinator], SelectEntity
):
    """Select entity for profile/sound mode."""

    _attr_has_entity_name = True
    _attr_translation_key = "profile_mode"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:volume-high"
    _attr_options = ["Sound", "Vibrate", "Silent"]

    _MODE_VALUES = {"Sound": "1", "Vibrate": "2", "Silent": "3"}

    def __init__(self, coordinator: One2TrackCoordinator, uuid: str) -> None:
        super().__init__(coordinator)
        self._uuid = uuid
        self._attr_unique_id = f"{uuid}_profile_mode"

    @property
    def device_info(self) -> dict[str, Any]:
        data = self.coordinator.data.get(self._uuid, {})
        return {
            "identifiers": {(DOMAIN, self._uuid)},
            "name": data.get("name", f"One2Track {self._uuid[:8]}"),
            "manufacturer": "One2Track",
            "model": data.get("device_model_name", "GPS Watch"),
        }

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
