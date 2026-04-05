"""Binary sensor platform for One2Track GPS."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import One2TrackConfigEntry
from .coordinator import One2TrackCoordinator
from .entity import One2TrackEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: One2TrackConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up One2Track binary sensors."""
    coordinator = entry.runtime_data

    entities: list[BinarySensorEntity] = []
    for uuid in coordinator.data:
        entities.append(One2TrackFallSensor(coordinator, uuid))

        # Add geofence binary sensors
        for geofence in coordinator.geofences.get(uuid, []):
            entities.append(
                One2TrackGeofenceSensor(coordinator, uuid, geofence)
            )

    async_add_entities(entities)


class One2TrackFallSensor(One2TrackEntity, BinarySensorEntity):
    """Binary sensor for fall/tumble detection."""

    _attr_translation_key = "fall_detected"
    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def __init__(self, coordinator: One2TrackCoordinator, uuid: str) -> None:
        super().__init__(coordinator, uuid)
        self._attr_unique_id = f"{uuid}_fall_detected"

    @property
    def is_on(self) -> bool | None:
        loc = self._device_data.get("last_location") or {}
        meta = loc.get("meta_data") or {}
        tumble = meta.get("tumble")
        if tumble is None:
            return None
        return str(tumble) == "1"


class One2TrackGeofenceSensor(One2TrackEntity, BinarySensorEntity):
    """Binary sensor for geofence presence."""

    _attr_device_class = BinarySensorDeviceClass.PRESENCE

    def __init__(
        self,
        coordinator: One2TrackCoordinator,
        uuid: str,
        geofence: dict[str, Any],
    ) -> None:
        super().__init__(coordinator, uuid)
        self._geofence_id = geofence.get("id")
        fence_name = geofence.get("name", f"Zone {self._geofence_id}")
        self._attr_unique_id = f"{uuid}_geofence_{self._geofence_id}"
        self._attr_translation_key = "geofence"
        self._attr_name = f"In {fence_name}"
        self._fence_lat = float(geofence.get("latitude", 0))
        self._fence_lon = float(geofence.get("longitude", 0))
        self._fence_radius = float(geofence.get("radius", 0))

    @property
    def is_on(self) -> bool | None:
        """Check if the device is inside the geofence."""
        loc = self._device_data.get("last_location") or {}
        try:
            lat = float(loc.get("latitude", 0))
            lon = float(loc.get("longitude", 0))
        except (ValueError, TypeError):
            return None

        if lat == 0 and lon == 0:
            return None

        # Haversine approximation for short distances
        import math

        d_lat = math.radians(lat - self._fence_lat)
        d_lon = math.radians(lon - self._fence_lon)
        a = (
            math.sin(d_lat / 2) ** 2
            + math.cos(math.radians(self._fence_lat))
            * math.cos(math.radians(lat))
            * math.sin(d_lon / 2) ** 2
        )
        distance_m = 6371000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return distance_m <= self._fence_radius
