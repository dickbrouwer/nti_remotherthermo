from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

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
    PLATFORMS,
    REFRESH_PATH,
    normalize_param_ids,
)

_LOGGER = logging.getLogger(__name__)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entry from an older version."""
    if entry.version == 1:
        _LOGGER.debug("Migrating config entry %s from version 1 to 2", entry.entry_id)
        new_data = {**entry.data}
        new_data.pop("token", None)
        new_data.setdefault(CONF_EMAIL, "")
        new_data.setdefault(CONF_PASSWORD, "")
        hass.config_entries.async_update_entry(entry, data=new_data, version=2)
        _LOGGER.info(
            "Config entry %s migrated to version 2; reauth will be required",
            entry.entry_id,
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up NTI RemoteThermo from a config entry."""
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from .api import NtiRemoteThermoApiClient
    from .coordinator import NtiRemoteThermoCoordinator

    hass.data.setdefault(DOMAIN, {})

    client_id = str(entry.data[CONF_CLIENT_ID]).strip()
    email = str(entry.data[CONF_EMAIL]).strip()
    password = str(entry.data[CONF_PASSWORD])

    param_ids = normalize_param_ids(
        entry.options.get(CONF_PARAM_IDS, DEFAULT_PARAM_IDS)
    )
    if not param_ids:
        param_ids = list(DEFAULT_PARAM_IDS)

    scan_interval = int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
    if scan_interval < 5:
        scan_interval = 5

    session = async_get_clientsession(hass)
    client = NtiRemoteThermoApiClient(
        session=session,
        base_url=BASE_URL,
        refresh_path=REFRESH_PATH,
        login_path=LOGIN_PATH,
        client_id=client_id,
        email=email,
        password=password,
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

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update by reloading the config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
