from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    BASE_URL,
    CONF_CLIENT_ID,
    CONF_PARAM_IDS,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    DEFAULT_PARAM_IDS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
    REFRESH_PATH,
)

_LOGGER = logging.getLogger(__name__)


def _normalize_param_ids(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [p.strip() for p in raw.split(",") if p.strip()]
    if isinstance(raw, list):
        return [str(p).strip() for p in raw if str(p).strip()]
    return []


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up integration namespace."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up NTI RemoteThermo from a config entry."""
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from .api import NtiRemoteThermoApiClient
    from .coordinator import NtiRemoteThermoCoordinator

    hass.data.setdefault(DOMAIN, {})

    client_id = str(entry.data[CONF_CLIENT_ID]).strip()
    token = str(entry.data[CONF_TOKEN]).strip()

    param_ids = _normalize_param_ids(
        entry.options.get(CONF_PARAM_IDS, DEFAULT_PARAM_IDS)
    )
    if not param_ids:
        param_ids = DEFAULT_PARAM_IDS

    scan_interval = int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
    if scan_interval < 5:
        scan_interval = 5

    session = async_get_clientsession(hass)
    client = NtiRemoteThermoApiClient(
        session=session,
        base_url=BASE_URL,
        refresh_path=REFRESH_PATH,
        client_id=client_id,
        token=token,
    )

    coordinator = NtiRemoteThermoCoordinator(
        hass=hass,
        client=client,
        param_ids=param_ids,
        scan_interval_s=scan_interval,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "client_id": client_id,
        "coordinator": coordinator,
        "param_ids": param_ids,
    }

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    data = hass.data[DOMAIN].get(entry.entry_id)
    if not data:
        return

    coordinator = data["coordinator"]

    param_ids = _normalize_param_ids(
        entry.options.get(CONF_PARAM_IDS, DEFAULT_PARAM_IDS)
    )
    if not param_ids:
        param_ids = DEFAULT_PARAM_IDS

    scan_interval = int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
    if scan_interval < 5:
        scan_interval = 5

    coordinator.set_params(param_ids, scan_interval)
    await coordinator.async_request_refresh()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
