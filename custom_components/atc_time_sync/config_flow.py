"""Config flow for ATC Time Sync integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.core import callback

from .const import DOMAIN, DEFAULT_BROADCAST_INTERVAL


class ATCTimeSyncConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ATC Time Sync."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            # Prevent duplicate entries
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title="ATC Time Sync",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("adapter", default="hci0"): str,
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow."""
        return ATCTimeSyncOptionsFlow(config_entry)


class ATCTimeSyncOptionsFlow(OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "broadcast_interval",
                        default=self.config_entry.options.get(
                            "broadcast_interval", DEFAULT_BROADCAST_INTERVAL
                        ),
                    ): vol.All(int, vol.Range(min=5, max=60)),
                }
            ),
        )
