"""Notify platform for One2Track GPS — send messages to watches."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.notify import (
    ATTR_TARGET,
    BaseNotificationService,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_get_service(
    hass: HomeAssistant,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> One2TrackNotifyService | None:
    """Get the One2Track notification service."""
    if discovery_info is None:
        return None

    coordinator = discovery_info["coordinator"]
    return One2TrackNotifyService(coordinator)


class One2TrackNotifyService(BaseNotificationService):
    """Send messages to One2Track watches."""

    def __init__(self, coordinator: Any) -> None:
        self._coordinator = coordinator

    @property
    def targets(self) -> dict[str, str]:
        """Return available targets (watches) keyed by name."""
        result = {}
        for uuid, device in self._coordinator.data.items():
            name = device.get("name", uuid)
            # Normalize name for use as target key
            key = name.lower().replace(" ", "_")
            result[key] = uuid
        return result

    async def async_send_message(self, message: str = "", **kwargs: Any) -> None:
        """Send a message to one or more watches."""
        targets = kwargs.get(ATTR_TARGET)

        if not targets:
            # Send to all watches
            for uuid in self._coordinator.data:
                await self._coordinator.api.send_message(uuid, message)
            return

        name_to_uuid = self.targets
        for target in targets:
            # Target can be a UUID directly or a device name
            uuid = name_to_uuid.get(target.lower().replace(" ", "_"), target)
            if uuid in self._coordinator.data:
                await self._coordinator.api.send_message(uuid, message)
            else:
                _LOGGER.warning("Unknown One2Track target: %s", target)
