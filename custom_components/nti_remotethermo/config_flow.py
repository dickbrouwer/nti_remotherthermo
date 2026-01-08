from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_CLIENT_ID,
    CONF_PARAM_IDS,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    DEFAULT_PARAM_IDS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)


class NtiRemoteThermoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for NTI RemoteThermo."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        if user_input is not None:
            client_id = str(user_input[CONF_CLIENT_ID]).strip()
            token = str(user_input[CONF_TOKEN]).strip()

            await self.async_set_unique_id(client_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"NTI RemoteThermo ({client_id})",
                data={
                    CONF_CLIENT_ID: client_id,
                    CONF_TOKEN: token,
                },
                options={
                    CONF_PARAM_IDS: DEFAULT_PARAM_IDS,
                    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                },
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_CLIENT_ID): str,
                vol.Required(CONF_TOKEN): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return NtiRemoteThermoOptionsFlow(config_entry)


class NtiRemoteThermoOptionsFlow(config_entries.OptionsFlow):
    """Options flow for NTI RemoteThermo."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        if user_input is not None:
            raw = str(user_input.get(CONF_PARAM_IDS, ""))
            param_ids = [p.strip() for p in raw.split(",") if p.strip()]

            scan_interval = int(
                user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            )
            if scan_interval < 5:
                scan_interval = 5

            return self.async_create_entry(
                title="",
                data={
                    CONF_PARAM_IDS: param_ids,
                    CONF_SCAN_INTERVAL: scan_interval,
                },
            )

        default_param_ids = self._entry.options.get(CONF_PARAM_IDS, DEFAULT_PARAM_IDS)
        if isinstance(default_param_ids, list):
            default_param_ids = ",".join(default_param_ids)

        schema = vol.Schema(
            {
                vol.Optional(CONF_PARAM_IDS, default=default_param_ids): str,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self._entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): vol.Coerce(int),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
