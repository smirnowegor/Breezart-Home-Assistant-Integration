"""Sensor platform for Breezart integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import UnitOfTemperature, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.entity import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, STATUS_MAP
from .coordinator import BreezartDataCoordinator


class BreezartSensor(CoordinatorEntity, SensorEntity):
    """Base class for Breezart sensors."""

    def __init__(
        self,
        coordinator: BreezartDataCoordinator,
        name: str,
        key: str,
        device_class: SensorDeviceClass | None = None,
        unit: str | None = None,
        entity_category: EntityCategory | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.client.host}_{key}"
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_entity_category = entity_category
        self._key = key

    @property
    def native_value(self) -> float | int | str | None:
        """Return the state of the sensor."""
        if self.coordinator.data:
            value = self.coordinator.data.get(self._key)
            if value is not None:
                if self._key == "current_temperature" or self._key in ["water_temperature", "outdoor_temperature"]:
                    return value / 10.0  # Convert from tenths of degrees
                elif self._key == "status":
                    return STATUS_MAP.get(value, f"Unknown ({value})")
                return value
        return None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.client.host)},
            name="Breezart 550 Aqua",
            manufacturer="Breezart",
            model="550 Aqua",
        )


class BreezartCurrentTemperatureSensor(BreezartSensor):
    """Sensor for current temperature."""

    def __init__(self, coordinator: BreezartDataCoordinator) -> None:
        super().__init__(
            coordinator,
            "Breezart Current Temperature",
            "current_temperature",
            SensorDeviceClass.TEMPERATURE,
            UnitOfTemperature.CELSIUS,
        )


class BreezartStatusSensor(BreezartSensor):
    """Sensor for system status."""

    def __init__(self, coordinator: BreezartDataCoordinator) -> None:
        super().__init__(
            coordinator,
            "Breezart Status",
            "status",
            entity_category=EntityCategory.DIAGNOSTIC,
        )


class BreezartFanSpeedSensor(BreezartSensor):
    """Sensor for current fan speed."""

    def __init__(self, coordinator: BreezartDataCoordinator) -> None:
        super().__init__(
            coordinator,
            "Breezart Fan Speed",
            "fan_speed_current",
            unit=PERCENTAGE,
        )


class BreezartWaterTemperatureSensor(BreezartSensor):
    """Sensor for water temperature."""

    def __init__(self, coordinator: BreezartDataCoordinator) -> None:
        super().__init__(
            coordinator,
            "Breezart Water Temperature",
            "water_temperature",
            SensorDeviceClass.TEMPERATURE,
            UnitOfTemperature.CELSIUS,
        )


class BreezartOutdoorTemperatureSensor(BreezartSensor):
    """Sensor for outdoor temperature."""

    def __init__(self, coordinator: BreezartDataCoordinator) -> None:
        super().__init__(
            coordinator,
            "Breezart Outdoor Temperature",
            "outdoor_temperature",
            SensorDeviceClass.TEMPERATURE,
            UnitOfTemperature.CELSIUS,
        )


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities
) -> None:
    """Set up Breezart sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = [
        BreezartCurrentTemperatureSensor(coordinator),
        BreezartStatusSensor(coordinator),
        BreezartFanSpeedSensor(coordinator),
        BreezartWaterTemperatureSensor(coordinator),
        BreezartOutdoorTemperatureSensor(coordinator),
    ]
    
    async_add_entities(entities)
