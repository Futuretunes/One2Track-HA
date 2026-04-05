"""Config flow for One2Track GPS."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback

from .api import One2TrackApiClient, One2TrackAuthError, One2TrackConnectionError
from .const import DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class One2TrackConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for One2Track GPS."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step — enter credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api = One2TrackApiClient(
                email=user_input[CONF_EMAIL],
                password=user_input[CONF_PASSWORD],
            )

            try:
                await api.authenticate()
            except One2TrackAuthError:
                errors["base"] = "invalid_auth"
            except One2TrackConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during login")
                errors["base"] = "unknown"
            else:
                # Prevent duplicate entries for the same account
                await self.async_set_unique_id(api.account_id)
                self._abort_if_unique_id_configured()

                await api.close()
                return self.async_create_entry(
                    title=user_input[CONF_EMAIL],
                    data=user_input,
                )
            finally:
                await api.close()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when credentials expire."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm re-authentication with new credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api = One2TrackApiClient(
                email=user_input[CONF_EMAIL],
                password=user_input[CONF_PASSWORD],
            )

            try:
                await api.authenticate()
            except One2TrackAuthError:
                errors["base"] = "invalid_auth"
            except One2TrackConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during re-auth")
                errors["base"] = "unknown"
            else:
                await api.close()
                entry = self.hass.config_entries.async_get_entry(
                    self.context["entry_id"]
                )
                if entry:
                    self.hass.config_entries.async_update_entry(
                        entry, data=user_input
                    )
                    await self.hass.config_entries.async_reload(entry.entry_id)
                    return self.async_abort(reason="reauth_successful")
            finally:
                await api.close()

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> One2TrackOptionsFlow:
        """Get the options flow handler."""
        return One2TrackOptionsFlow(config_entry)


class One2TrackOptionsFlow(OptionsFlow):
    """Handle options for One2Track GPS."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self._config_entry.options.get(
            "update_interval", DEFAULT_UPDATE_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "update_interval", default=current_interval
                    ): vol.All(vol.Coerce(int), vol.Range(min=30, max=300)),
                }
            ),
        )
