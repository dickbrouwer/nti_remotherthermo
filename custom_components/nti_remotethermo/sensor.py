from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

# Map unit labels from the API to HA device classes and standard units.
# Keys are lowercased for case-insensitive matching.
UNIT_DEVICE_CLASS_MAP: dict[str, SensorDeviceClass] = {
    "°c": SensorDeviceClass.TEMPERATURE,
    "degc": SensorDeviceClass.TEMPERATURE,
    "°f": SensorDeviceClass.TEMPERATURE,
    "degf": SensorDeviceClass.TEMPERATURE,
    "bar": SensorDeviceClass.PRESSURE,
    "mbar": SensorDeviceClass.PRESSURE,
    "psi": SensorDeviceClass.PRESSURE,
    "kpa": SensorDeviceClass.PRESSURE,
    "hpa": SensorDeviceClass.PRESSURE,
    "%": SensorDeviceClass.POWER_FACTOR,
    "kwh": SensorDeviceClass.ENERGY,
    "kw": SensorDeviceClass.POWER,
    "w": SensorDeviceClass.POWER,
    "l/min": SensorDeviceClass.VOLUME_FLOW_RATE,
    "m³/h": SensorDeviceClass.VOLUME_FLOW_RATE,
}


@dataclass(frozen=True, kw_only=True)
class NtiParamSensorDescription(SensorEntityDescription):
    param_id: str


def _safe_label(item: dict[str, Any]) -> str:
    label = item.get("label")
    if isinstance(label, str) and label.strip():
        return label.strip()
    return str(item.get("id", "NTI Sensor"))


def _device_class_from_unit(unit: str | None) -> SensorDeviceClass | None:
    """Infer device class from the API unit label."""
    if not unit or not isinstance(unit, str):
        return None
    return UNIT_DEVICE_CLASS_MAP.get(unit.strip().lower())


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
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
        self._client_id = client_id
        self._attr_unique_id = f"{DOMAIN}_{client_id}_{description.param_id}"

    @property
    def device_info(self) -> DeviceInfo:
        """Group all sensors under a single device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._client_id)},
            name=f"NTI RemoteThermo ({self._client_id})",
            manufacturer="NTI",
        )

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
    def device_class(self) -> SensorDeviceClass | None:
        """Infer device class from the unit label."""
        return _device_class_from_unit(self.native_unit_of_measurement)

    @property
    def state_class(self) -> SensorStateClass | None:
        """Only report MEASUREMENT for numeric values."""
        value = self.native_value
        if isinstance(value, (int, float)):
            return SensorStateClass.MEASUREMENT
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
