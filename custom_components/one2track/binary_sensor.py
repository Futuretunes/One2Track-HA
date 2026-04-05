"""Binary sensor platform for One2Track GPS."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import One2TrackConfigEntry
from .const import DOMAIN
from .coordinator import One2TrackCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: One2TrackConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up One2Track binary sensors."""
    coordinator = entry.runtime_data

    async_add_entities(
        One2TrackFallSensor(coordinator, uuid)
        for uuid in coordinator.data
    )


class One2TrackFallSensor(CoordinatorEntity[One2TrackCoordinator], BinarySensorEntity):
    """Binary sensor for fall/tumble detection."""

    _attr_has_entity_name = True
    _attr_translation_key = "fall_detected"
    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def __init__(self, coordinator: One2TrackCoordinator, uuid: str) -> None:
        super().__init__(coordinator)
        self._uuid = uuid
        self._attr_unique_id = f"{uuid}_fall_detected"

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
    def is_on(self) -> bool | None:
        data = self.coordinator.data.get(self._uuid, {})
        loc = data.get("last_location") or {}
        meta = loc.get("meta_data") or {}
        tumble = meta.get("tumble")
        if tumble is None:
            return None
        return str(tumble) == "1"
