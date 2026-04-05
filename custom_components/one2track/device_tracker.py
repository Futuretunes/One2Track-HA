"""Device tracker platform for One2Track GPS."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import One2TrackConfigEntry
from .const import DOMAIN
from .coordinator import One2TrackCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: One2TrackConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up One2Track device trackers."""
    coordinator = entry.runtime_data

    async_add_entities(
        One2TrackDeviceTracker(coordinator, uuid)
        for uuid in coordinator.data
    )


class One2TrackDeviceTracker(CoordinatorEntity[One2TrackCoordinator], TrackerEntity):
    """Represent a One2Track GPS watch on the map."""

    _attr_has_entity_name = True
    _attr_name = None  # Use device name

    def __init__(self, coordinator: One2TrackCoordinator, uuid: str) -> None:
        super().__init__(coordinator)
        self._uuid = uuid
        self._attr_unique_id = f"{uuid}_tracker"

    @property
    def _device_data(self) -> dict[str, Any]:
        return self.coordinator.data.get(self._uuid, {})

    @property
    def _location_data(self) -> dict[str, Any]:
        return self._device_data.get("last_location") or {}

    @property
    def device_info(self) -> dict[str, Any]:
        data = self._device_data
        return {
            "identifiers": {(DOMAIN, self._uuid)},
            "name": data.get("name", f"One2Track {self._uuid[:8]}"),
            "manufacturer": "One2Track",
            "model": data.get("device_model_name", "GPS Watch"),
            "serial_number": data.get("serial_number"),
        }

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        lat = self._location_data.get("latitude")
        if lat is not None:
            try:
                return float(lat)
            except (ValueError, TypeError):
                return None
        return None

    @property
    def longitude(self) -> float | None:
        lon = self._location_data.get("longitude")
        if lon is not None:
            try:
                return float(lon)
            except (ValueError, TypeError):
                return None
        return None

    @property
    def battery_level(self) -> int | None:
        return self._location_data.get("battery_percentage")

    @property
    def location_accuracy(self) -> int:
        meta = self._location_data.get("meta_data") or {}
        accuracy = meta.get("accuracy_meters")
        if accuracy is not None:
            try:
                return int(float(accuracy))
            except (ValueError, TypeError):
                pass
        # Fallback: GPS is ~10m, WiFi/LBS is ~100m
        loc_type = self._location_data.get("location_type", "")
        if loc_type == "GPS":
            return 10
        return 100

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        loc = self._location_data
        meta = loc.get("meta_data") or {}
        attrs: dict[str, Any] = {}

        if addr := loc.get("address"):
            attrs["address"] = addr
        if loc_type := loc.get("location_type"):
            attrs["location_type"] = loc_type
        if last_comm := loc.get("last_communication"):
            attrs["last_communication"] = last_comm
        if course := meta.get("course"):
            attrs["heading"] = course

        return attrs
