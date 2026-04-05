"""Service handlers for One2Track GPS."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import CMD_PHONEBOOK, CMD_QUIET_TIMES, DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_SEND_MESSAGE = "send_message"
SERVICE_SET_PHONEBOOK = "set_phonebook"
SERVICE_SET_QUIET_TIMES = "set_quiet_times"

SEND_MESSAGE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Required("message"): cv.string,
    }
)

SET_PHONEBOOK_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Required("entries"): vol.All(
            cv.ensure_list,
            [
                vol.Schema(
                    {
                        vol.Required("name"): cv.string,
                        vol.Required("number"): cv.string,
                    }
                )
            ],
        ),
    }
)

SET_QUIET_TIMES_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Required("enabled"): cv.boolean,
        vol.Optional("start_time", default="22:00"): cv.string,
        vol.Optional("end_time", default="07:00"): cv.string,
    }
)


def _get_coordinator(hass: HomeAssistant, device_id: str) -> Any:
    """Get the coordinator for a device by device UUID."""
    for entry_data in hass.data.get(DOMAIN, {}).values():
        if hasattr(entry_data, "data") and device_id in entry_data.data:
            return entry_data
    # Also try matching by device registry
    for entry_id in hass.data.get(DOMAIN, {}):
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry and hasattr(entry, "runtime_data"):
            coordinator = entry.runtime_data
            if device_id in coordinator.data:
                return coordinator
    return None


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up One2Track services."""

    async def handle_send_message(call: ServiceCall) -> None:
        """Handle send_message service call."""
        device_id = call.data["device_id"]
        message = call.data["message"]

        coordinator = _get_coordinator(hass, device_id)
        if not coordinator:
            _LOGGER.error("Device %s not found", device_id)
            return

        await coordinator.api.send_message(device_id, message)

    async def handle_set_phonebook(call: ServiceCall) -> None:
        """Handle set_phonebook service call."""
        device_id = call.data["device_id"]
        entries = call.data["entries"]

        coordinator = _get_coordinator(hass, device_id)
        if not coordinator:
            _LOGGER.error("Device %s not found", device_id)
            return

        # Build phonebook values: alternating name, number pairs
        values = []
        for entry in entries[:10]:  # Max 10 phonebook entries
            values.append(entry["name"])
            values.append(entry["number"])

        await coordinator.api.send_command(device_id, CMD_PHONEBOOK, values)

    async def handle_set_quiet_times(call: ServiceCall) -> None:
        """Handle set_quiet_times service call."""
        device_id = call.data["device_id"]
        enabled = call.data["enabled"]
        start_time = call.data["start_time"]
        end_time = call.data["end_time"]

        coordinator = _get_coordinator(hass, device_id)
        if not coordinator:
            _LOGGER.error("Device %s not found", device_id)
            return

        values = [
            "1" if enabled else "0",
            start_time,
            end_time,
        ]
        await coordinator.api.send_command(device_id, CMD_QUIET_TIMES, values)

    hass.services.async_register(
        DOMAIN, SERVICE_SEND_MESSAGE, handle_send_message, schema=SEND_MESSAGE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_PHONEBOOK, handle_set_phonebook, schema=SET_PHONEBOOK_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_QUIET_TIMES, handle_set_quiet_times, schema=SET_QUIET_TIMES_SCHEMA
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload One2Track services."""
    hass.services.async_remove(DOMAIN, SERVICE_SEND_MESSAGE)
    hass.services.async_remove(DOMAIN, SERVICE_SET_PHONEBOOK)
    hass.services.async_remove(DOMAIN, SERVICE_SET_QUIET_TIMES)
