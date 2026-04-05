"""Base entity for One2Track GPS."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_MODELS, DOMAIN
from .coordinator import One2TrackCoordinator


class One2TrackEntity(CoordinatorEntity[One2TrackCoordinator]):
    """Base class for One2Track entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: One2TrackCoordinator, uuid: str) -> None:
        super().__init__(coordinator)
        self._uuid = uuid

    @property
    def _device_data(self) -> dict[str, Any]:
        return self.coordinator.data.get(self._uuid, {})

    @property
    def device_info(self) -> DeviceInfo:
        data = self._device_data
        model_id = data.get("device_model_id")
        model_name = DEVICE_MODELS.get(model_id, "GPS Watch") if model_id else "GPS Watch"
        return DeviceInfo(
            identifiers={(DOMAIN, self._uuid)},
            name=data.get("name", f"One2Track {self._uuid[:8]}"),
            manufacturer="One2Track",
            model=model_name,
            serial_number=data.get("serial_number"),
        )
