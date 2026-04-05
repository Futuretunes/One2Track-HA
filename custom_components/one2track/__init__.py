"""The One2Track GPS integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant

from .api import One2TrackApiClient
from .const import DOMAIN
from .coordinator import One2TrackCoordinator
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.DEVICE_TRACKER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TEXT,
]

type One2TrackConfigEntry = ConfigEntry[One2TrackCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: One2TrackConfigEntry) -> bool:
    """Set up One2Track GPS from a config entry."""
    api = One2TrackApiClient(
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
    )

    try:
        await api.authenticate()
    except Exception:
        await api.close()
        raise

    update_interval = entry.options.get("update_interval", 60)
    coordinator = One2TrackCoordinator(hass, api, update_interval)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await async_setup_services(hass)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: One2TrackConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        await entry.runtime_data.api.close()

        # Only unload services if no other entries remain
        remaining = [
            e for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != entry.entry_id
        ]
        if not remaining:
            await async_unload_services(hass)

    return unload_ok


async def _async_update_listener(
    hass: HomeAssistant, entry: One2TrackConfigEntry
) -> None:
    """Handle options update — reload the integration."""
    await hass.config_entries.async_reload(entry.entry_id)
