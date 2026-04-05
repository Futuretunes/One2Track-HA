"""Switch platform for One2Track GPS."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import One2TrackConfigEntry
from .const import CMD_STEP_COUNTERS
from .coordinator import One2TrackCoordinator
from .entity import One2TrackEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: One2TrackConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up One2Track switches."""
    coordinator = entry.runtime_data

    entities: list[SwitchEntity] = []
    for uuid in coordinator.data:
        caps = coordinator.device_capabilities.get(uuid, [])
        step_cmd = next((c for c in caps if c in CMD_STEP_COUNTERS), None)
        if step_cmd:
            entities.append(One2TrackStepCounterSwitch(coordinator, uuid, step_cmd))

    async_add_entities(entities)


class One2TrackStepCounterSwitch(One2TrackEntity, SwitchEntity):
    """Switch to toggle the step counter on a One2Track watch."""

    _attr_translation_key = "step_counter"
    _attr_icon = "mdi:shoe-print"

    def __init__(
        self, coordinator: One2TrackCoordinator, uuid: str, cmd_code: str,
    ) -> None:
        super().__init__(coordinator, uuid)
        self._cmd_code = cmd_code
        self._attr_unique_id = f"{uuid}_step_counter"
        self._assumed_state = True

    @property
    def is_on(self) -> bool | None:
        loc = self._device_data.get("last_location") or {}
        meta = loc.get("meta_data") or {}
        steps = meta.get("steps")
        if steps is not None:
            try:
                return int(steps) > 0
            except (ValueError, TypeError):
                pass
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the step counter."""
        await self.coordinator.api.send_command(
            self._uuid, self._cmd_code, ["1"]
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the step counter."""
        await self.coordinator.api.send_command(
            self._uuid, self._cmd_code, ["0"]
        )
