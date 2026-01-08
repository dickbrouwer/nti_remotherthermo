from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


@dataclass(frozen=True, kw_only=True)
class NtiParamSensorDescription(SensorEntityDescription):
    param_id: str


def _safe_label(item: dict[str, Any]) -> str:
    label = item.get("label")
    if isinstance(label, str) and label.strip():
        return label.strip()
    return str(item.get("id", "NTI Sensor"))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]  # set in __init__.py
    coordinator = data["coordinator"]
    client_id: str = data["client_id"]
    param_ids: list[str] = data["param_ids"]

    entities: list[SensorEntity] = []
    for pid in param_ids:
        desc = NtiParamSensorDescription(
            key=pid,
            name=f"NTI {pid}",
            param_id=pid,
        )
        entities.append(NtiRemoteThermoParamSensor(coordinator, desc, client_id))

    async_add_entities(entities, True)


class NtiRemoteThermoParamSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing one NTI paramId entry."""

    entity_description: NtiParamSensorDescription

    def __init__(
        self, coordinator, description: NtiParamSensorDescription, client_id: str
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{client_id}_{description.param_id}"

    @property
    def _item(self) -> dict[str, Any] | None:
        data = self.coordinator.data
        if isinstance(data, dict):
            item = data.get(self.entity_description.param_id)
            if isinstance(item, dict):
                return item
        return None

    @property
    def name(self) -> str:
        item = self._item
        if item:
            return _safe_label(item)
        return self.entity_description.name

    @property
    def native_value(self) -> Any:
        item = self._item
        if not item:
            return None
        return item.get("value")

    @property
    def native_unit_of_measurement(self) -> str | None:
        item = self._item
        if not item:
            return None
        unit = item.get("unitLabel")
        if isinstance(unit, str) and unit.strip():
            return unit.strip()
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        item = self._item
        if not item:
            return {}
        return {
            "param_id": item.get("id"),
            "fullIdentifier": item.get("fullIdentifier"),
            "readOnly": item.get("readOnly"),
            "decimals": item.get("decimals"),
            "min": item.get("min"),
            "max": item.get("max"),
            "anyError": item.get("anyError"),
        }

    @property
    def state_class(self) -> SensorStateClass | None:
        return SensorStateClass.MEASUREMENT
