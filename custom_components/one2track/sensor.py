"""Sensor platform for One2Track GPS."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS,
    EntityCategory,
    UnitOfLength,
    UnitOfSpeed,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import One2TrackConfigEntry
from .const import DOMAIN
from .coordinator import One2TrackCoordinator


@dataclass(frozen=True, kw_only=True)
class One2TrackSensorDescription(SensorEntityDescription):
    """Describe a One2Track sensor."""

    value_fn: str  # dot-separated path into device data
    convert: str | None = None  # "float", "int", "cents_to_eur"


SENSOR_DESCRIPTIONS: tuple[One2TrackSensorDescription, ...] = (
    One2TrackSensorDescription(
        key="battery",
        translation_key="battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn="last_location.battery_percentage",
        convert="int",
    ),
    One2TrackSensorDescription(
        key="signal_strength",
        translation_key="signal_strength",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn="last_location.signal_strength",
        convert="int",
    ),
    One2TrackSensorDescription(
        key="satellite_count",
        translation_key="satellite_count",
        icon="mdi:satellite-variant",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn="last_location.satellite_count",
        convert="int",
    ),
    One2TrackSensorDescription(
        key="speed",
        translation_key="speed",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn="last_location.speed",
        convert="float",
    ),
    One2TrackSensorDescription(
        key="altitude",
        translation_key="altitude",
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn="last_location.altitude",
        convert="float",
    ),
    One2TrackSensorDescription(
        key="steps",
        translation_key="steps",
        icon="mdi:shoe-print",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn="last_location.meta_data.steps",
        convert="int",
    ),
    One2TrackSensorDescription(
        key="sim_balance",
        translation_key="sim_balance",
        icon="mdi:currency-eur",
        native_unit_of_measurement="EUR",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn="simcard.balance_cents",
        convert="cents_to_eur",
    ),
    One2TrackSensorDescription(
        key="last_communication",
        translation_key="last_communication",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn="last_location.last_communication",
        convert="timestamp",
    ),
    One2TrackSensorDescription(
        key="last_location_update",
        translation_key="last_location_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn="last_location.last_location_update",
        convert="timestamp",
    ),
    One2TrackSensorDescription(
        key="location_type",
        translation_key="location_type",
        icon="mdi:crosshairs-gps",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn="last_location.location_type",
    ),
    One2TrackSensorDescription(
        key="status",
        translation_key="status",
        icon="mdi:watch",
        value_fn="status",
    ),
)


def _resolve_value(data: dict[str, Any], path: str) -> Any:
    """Resolve a dot-separated path into nested dict data."""
    current = data
    for key in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(key)
        if current is None:
            return None
    return current


def _convert_value(raw: Any, convert: str | None) -> StateType:
    """Convert a raw API value to a sensor state."""
    if raw is None:
        return None
    if convert == "int":
        try:
            return int(raw)
        except (ValueError, TypeError):
            return None
    if convert == "float":
        try:
            return float(raw)
        except (ValueError, TypeError):
            return None
    if convert == "cents_to_eur":
        try:
            return round(float(raw) / 100, 2)
        except (ValueError, TypeError):
            return None
    if convert == "timestamp":
        try:
            dt = datetime.fromisoformat(str(raw))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except (ValueError, TypeError):
            return None
    # No conversion — return as string
    if isinstance(raw, (int, float)):
        return raw
    return str(raw) if raw else None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: One2TrackConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up One2Track sensors."""
    coordinator = entry.runtime_data

    entities: list[One2TrackSensor] = []
    for uuid in coordinator.data:
        for description in SENSOR_DESCRIPTIONS:
            entities.append(One2TrackSensor(coordinator, uuid, description))

    async_add_entities(entities)


class One2TrackSensor(CoordinatorEntity[One2TrackCoordinator], SensorEntity):
    """A sensor for a One2Track GPS watch."""

    _attr_has_entity_name = True
    entity_description: One2TrackSensorDescription

    def __init__(
        self,
        coordinator: One2TrackCoordinator,
        uuid: str,
        description: One2TrackSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self._uuid = uuid
        self.entity_description = description
        self._attr_unique_id = f"{uuid}_{description.key}"

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
    def native_value(self) -> StateType:
        data = self.coordinator.data.get(self._uuid, {})
        raw = _resolve_value(data, self.entity_description.value_fn)
        return _convert_value(raw, self.entity_description.convert)
