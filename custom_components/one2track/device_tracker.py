"""Device tracker platform for One2Track GPS."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import One2TrackConfigEntry
from .const import STALE_LOCATION_MINUTES
from .coordinator import One2TrackCoordinator
from .entity import One2TrackEntity

_LOGGER = logging.getLogger(__name__)

_LOCATION_TYPE_ICONS = {
    "GPS": "mdi:crosshairs-gps",
    "WIFI": "mdi:wifi",
    "LBS": "mdi:cellphone-wireless",
}


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


class One2TrackDeviceTracker(One2TrackEntity, TrackerEntity):
    """Represent a One2Track GPS watch on the map."""

    _attr_name = None  # Use device name

    def __init__(self, coordinator: One2TrackCoordinator, uuid: str) -> None:
        super().__init__(coordinator, uuid)
        self._attr_unique_id = f"{uuid}_tracker"

    @property
    def _location_data(self) -> dict[str, Any]:
        return self._device_data.get("last_location") or {}

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def icon(self) -> str:
        loc_type = self._location_data.get("location_type", "")
        return _LOCATION_TYPE_ICONS.get(loc_type, "mdi:crosshairs-gps")

    @property
    def available(self) -> bool:
        """Mark unavailable if location data is stale."""
        if not super().available:
            return False
        loc = self._location_data
        last_update = loc.get("last_location_update") or loc.get("last_communication")
        if not last_update:
            return False
        try:
            dt = datetime.fromisoformat(str(last_update))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            age_minutes = (now - dt).total_seconds() / 60
            return age_minutes < STALE_LOCATION_MINUTES
        except (ValueError, TypeError):
            return True

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
        # Fallback based on location type
        loc_type = self._location_data.get("location_type", "")
        if loc_type == "GPS":
            return 10
        if loc_type == "WIFI":
            return 50
        return 100  # LBS / unknown

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
        if accuracy := meta.get("accuracy_meters"):
            attrs["accuracy_meters"] = accuracy

        return attrs
