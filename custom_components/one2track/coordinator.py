"""DataUpdateCoordinator for One2Track GPS."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import One2TrackApiClient, One2TrackAuthError, One2TrackConnectionError
from .const import DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class One2TrackCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Coordinator that fetches all device data from One2Track."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        api: One2TrackApiClient,
        update_interval: int = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )
        self.api = api
        self.device_capabilities: dict[str, list[str]] = {}
        self._capabilities_fetched = False

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch device data from One2Track."""
        try:
            devices = await self.api.get_devices()
        except One2TrackAuthError as err:
            raise ConfigEntryAuthFailed(
                f"Authentication failed: {err}"
            ) from err
        except One2TrackConnectionError as err:
            raise UpdateFailed(f"Error communicating with One2Track: {err}") from err

        # Build dict keyed by UUID
        result: dict[str, dict[str, Any]] = {}
        for device in devices:
            uuid = device.get("uuid")
            if uuid:
                result[uuid] = device

        # Fetch capabilities once on first successful data load
        if not self._capabilities_fetched and result:
            self._capabilities_fetched = True
            for uuid in result:
                try:
                    caps = await self.api.get_device_capabilities(uuid)
                    self.device_capabilities[uuid] = caps
                    _LOGGER.debug(
                        "Device %s capabilities: %s", uuid, caps
                    )
                except Exception:  # noqa: BLE001
                    _LOGGER.warning(
                        "Could not fetch capabilities for %s", uuid
                    )
                    self.device_capabilities[uuid] = []

        return result
