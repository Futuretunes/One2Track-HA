"""Button platform for One2Track GPS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import One2TrackConfigEntry
from .const import CMD_FIND_DEVICE, CMD_REFRESH_LOCATION, CMD_REMOTE_SHUTDOWN
from .coordinator import One2TrackCoordinator
from .entity import One2TrackEntity


@dataclass(frozen=True, kw_only=True)
class One2TrackButtonDescription(ButtonEntityDescription):
    """Describe a One2Track button."""

    cmd_code: str


BUTTON_DESCRIPTIONS: tuple[One2TrackButtonDescription, ...] = (
    One2TrackButtonDescription(
        key="refresh_location",
        translation_key="refresh_location",
        icon="mdi:crosshairs-gps",
        cmd_code=CMD_REFRESH_LOCATION,
    ),
    One2TrackButtonDescription(
        key="find_device",
        translation_key="find_device",
        icon="mdi:bell-ring",
        cmd_code=CMD_FIND_DEVICE,
    ),
    One2TrackButtonDescription(
        key="remote_shutdown",
        translation_key="remote_shutdown",
        icon="mdi:power",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        cmd_code=CMD_REMOTE_SHUTDOWN,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: One2TrackConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up One2Track buttons."""
    coordinator = entry.runtime_data

    entities: list[One2TrackButton] = []
    for uuid in coordinator.data:
        caps = coordinator.device_capabilities.get(uuid, [])
        for description in BUTTON_DESCRIPTIONS:
            if not caps or description.cmd_code in caps:
                entities.append(One2TrackButton(coordinator, uuid, description))

    async_add_entities(entities)


class One2TrackButton(One2TrackEntity, ButtonEntity):
    """A button that sends a command to a One2Track watch."""

    entity_description: One2TrackButtonDescription

    def __init__(
        self,
        coordinator: One2TrackCoordinator,
        uuid: str,
        description: One2TrackButtonDescription,
    ) -> None:
        super().__init__(coordinator, uuid)
        self.entity_description = description
        self._attr_unique_id = f"{uuid}_{description.key}"

    async def async_press(self) -> None:
        """Send the command when the button is pressed."""
        await self.coordinator.api.send_command(
            self._uuid, self.entity_description.cmd_code
        )
        await self.coordinator.async_request_refresh()
