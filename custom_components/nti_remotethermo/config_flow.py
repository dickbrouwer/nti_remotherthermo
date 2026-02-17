from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    NtiRemoteThermoApiClient,
    NtiRemoteThermoApiError,
    NtiRemoteThermoAuthError,
)
from .const import (
    BASE_URL,
    CONF_CLIENT_ID,
    CONF_EMAIL,
    CONF_PARAM_IDS,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    DEFAULT_PARAM_IDS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGIN_PATH,
    REFRESH_PATH,
    normalize_param_ids,
)

_LOGGER = logging.getLogger(__name__)


class NtiRemoteThermoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for NTI RemoteThermo."""

    VERSION = 2

    async def _test_credentials(
        self, client_id: str, email: str, password: str
    ) -> str | None:
        """Test credentials against the API. Returns error key or None on success."""
        session = async_get_clientsession(self.hass)
        client = NtiRemoteThermoApiClient(
            session=session,
            base_url=BASE_URL,
            refresh_path=REFRESH_PATH,
            login_path=LOGIN_PATH,
            client_id=client_id,
            email=email,
            password=password,
        )
        try:
            payload = await client.fetch(list(DEFAULT_PARAM_IDS[:1]))
        except NtiRemoteThermoAuthError:
            return "invalid_auth"
        except NtiRemoteThermoApiError:
            return "cannot_connect"
        except Exception:
            _LOGGER.exception("Unexpected error during credential test")
            return "unknown"

        if not isinstance(payload, dict) or payload.get("ok") is not True:
            return "cannot_connect"

        return None

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client_id = str(user_input[CONF_CLIENT_ID]).strip()
            email = str(user_input[CONF_EMAIL]).strip()
            password = str(user_input[CONF_PASSWORD])

            error = await self._test_credentials(client_id, email, password)
            if error:
                errors["base"] = error
            else:
                await self.async_set_unique_id(client_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"NTI RemoteThermo ({client_id})",
                    data={
                        CONF_CLIENT_ID: client_id,
                        CONF_EMAIL: email,
                        CONF_PASSWORD: password,
                    },
                    options={
                        CONF_PARAM_IDS: list(DEFAULT_PARAM_IDS),
                        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_CLIENT_ID): str,
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.PASSWORD
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    async def async_step_reauth(self, entry_data: dict) -> FlowResult:
        """Handle re-authentication when credentials expire."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None) -> FlowResult:
        """Handle re-authentication confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            entry = self.hass.config_entries.async_get_entry(
                self.context["entry_id"]
            )
            client_id = str(entry.data[CONF_CLIENT_ID]).strip()
            email = str(user_input[CONF_EMAIL]).strip()
            password = str(user_input[CONF_PASSWORD])

            error = await self._test_credentials(client_id, email, password)
            if error:
                errors["base"] = error
            else:
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={
                        **entry.data,
                        CONF_EMAIL: email,
                        CONF_PASSWORD: password,
                    },
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        schema = vol.Schema(
            {
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.PASSWORD
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="reauth_confirm", data_schema=schema, errors=errors
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> NtiRemoteThermoOptionsFlow:
        """Get the options flow handler."""
        return NtiRemoteThermoOptionsFlow()


class NtiRemoteThermoOptionsFlow(config_entries.OptionsFlow):
    """Options flow for NTI RemoteThermo."""

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Handle options step."""
        if user_input is not None:
            param_ids = normalize_param_ids(
                user_input.get(CONF_PARAM_IDS, "")
            )

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

        default_param_ids = self.config_entry.options.get(
            CONF_PARAM_IDS, DEFAULT_PARAM_IDS
        )
        if isinstance(default_param_ids, list):
            default_param_ids = ",".join(default_param_ids)

        schema = vol.Schema(
            {
                vol.Optional(CONF_PARAM_IDS, default=default_param_ids): str,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): vol.Coerce(int),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
