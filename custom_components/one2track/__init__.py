"""The One2Track GPS integration."""

from __future__ import annotations

import logging

from homeassistant.components.notify import DOMAIN as NOTIFY_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery import async_load_platform

from .api import One2TrackApiClient
from .const import DOMAIN
from .coordinator import One2TrackCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.DEVICE_TRACKER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
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

    # Set up notify platform via discovery
    hass.async_create_task(
        async_load_platform(
            hass,
            NOTIFY_DOMAIN,
            DOMAIN,
            {"coordinator": coordinator},
            {},
        )
    )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: One2TrackConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        await entry.runtime_data.api.close()

    return unload_ok


async def _async_update_listener(
    hass: HomeAssistant, entry: One2TrackConfigEntry
) -> None:
    """Handle options update — reload the integration."""
    await hass.config_entries.async_reload(entry.entry_id)
