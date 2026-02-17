from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SETPOINT_PARAM_ID = "T4_0_2"
SETPOINT_MIN = 90
SETPOINT_MAX = 140
SETPOINT_STEP = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    client_id: str = data["client_id"]
    client = data["client"]

    async_add_entities(
        [NtiRemoteThermoSetpointNumber(coordinator, client, client_id)],
        True,
    )


class NtiRemoteThermoSetpointNumber(CoordinatorEntity, NumberEntity):
    """Number entity for the Zone CH setpoint temperature."""

    _attr_mode = NumberMode.BOX
    _attr_native_min_value = SETPOINT_MIN
    _attr_native_max_value = SETPOINT_MAX
    _attr_native_step = SETPOINT_STEP
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT

    def __init__(self, coordinator, client, client_id: str) -> None:
        super().__init__(coordinator)
        self._client = client
        self._client_id = client_id
        self._attr_unique_id = f"{DOMAIN}_{client_id}_{SETPOINT_PARAM_ID}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._client_id)},
            name=f"NTI RemoteThermo ({self._client_id})",
            manufacturer="NTI",
        )

    @property
    def _item(self) -> dict[str, Any] | None:
        data = self.coordinator.data
        if isinstance(data, dict):
            item = data.get(SETPOINT_PARAM_ID)
            if isinstance(item, dict):
                return item
        return None

    @property
    def name(self) -> str:
        item = self._item
        if item:
            label = item.get("label")
            if isinstance(label, str) and label.strip():
                return label.strip()
        return "T set Z1"

    @property
    def native_value(self) -> float | None:
        item = self._item
        if not item:
            return None
        value = item.get("value")
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        int_value = int(value)
        _LOGGER.debug(
            "Setting %s to %s (client_id=%s)",
            SETPOINT_PARAM_ID,
            int_value,
            self._client_id,
        )
        await self._client.submit(SETPOINT_PARAM_ID, int_value)
        await self.coordinator.async_request_refresh()
