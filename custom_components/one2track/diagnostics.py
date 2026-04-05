"""Diagnostics for One2Track GPS."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import One2TrackConfigEntry

REDACT_KEYS = {
    "password",
    "email",
    "phone_number",
    "serial_number",
    "latitude",
    "longitude",
    "address",
    "macAddress",
    "name",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: One2TrackConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data

    device_data = {}
    for uuid, data in coordinator.data.items():
        device_data[uuid] = async_redact_data(data, REDACT_KEYS)

    return {
        "config_entry": {
            "title": entry.title,
            "options": dict(entry.options),
        },
        "devices": device_data,
        "capabilities": coordinator.device_capabilities,
        "geofences": {
            uuid: [
                async_redact_data(f, {"latitude", "longitude", "name"})
                for f in fences
            ]
            for uuid, fences in coordinator.geofences.items()
        },
    }
