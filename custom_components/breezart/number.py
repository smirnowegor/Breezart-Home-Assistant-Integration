"""Number platform for Breezart integration."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberDeviceClass
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.entity import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, REG_TARGET_TEMP, REG_FAN_SPEED_SET
from .coordinator import BreezartDataCoordinator


class BreezartNumber(CoordinatorEntity, NumberEntity):
    """Base class for Breezart numbers."""

    def __init__(
        self,
        coordinator: BreezartDataCoordinator,
        name: str,
        key: str,
        min_value: float,
        max_value: float,
        step: float,
        device_class: NumberDeviceClass | None = None,
        unit: str | None = None,
        entity_category: EntityCategory | None = None,
    ) -> None:
        """Initialize the number."""
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.client.host}_{key}"
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_entity_category = entity_category
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._key = key
        self._register = REG_TARGET_TEMP if key == "target_temperature" else REG_FAN_SPEED_SET

    @property
    def native_value(self) -> float | None:
        """Return the state of the number."""
        # TODO: Read actual value from device
        # For now, return a reasonable default
        if self._key == "target_temperature":
            return 22.0
        else:
            return 5.0

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        if self._key == "target_temperature":
            # Convert to tenths of degrees for the device
            device_value = int(value * 10)
        else:
            device_value = int(value)
        
        await self.coordinator.write_register(self._register, device_value)
        self._attr_native_value = value
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.client.host)},
            name="Breezart 550 Aqua",
            manufacturer="Breezart",
            model="550 Aqua",
        )


class BreezartTargetTemperatureNumber(BreezartNumber):
    """Number for target temperature."""

    def __init__(self, coordinator: BreezartDataCoordinator) -> None:
        super().__init__(
            coordinator,
            "Breezart Target Temperature",
            "target_temperature",
            min_value=15.0,
            max_value=30.0,
            step=0.5,
            device_class=NumberDeviceClass.TEMPERATURE,
            unit=UnitOfTemperature.CELSIUS,
        )


class BreezartFanSpeedNumber(BreezartNumber):
    """Number for fan speed."""

    def __init__(self, coordinator: BreezartDataCoordinator) -> None:
        super().__init__(
            coordinator,
            "Breezart Fan Speed",
            "fan_speed_set",
            min_value=0.0,
            max_value=10.0,
            step=1.0,
            entity_category=EntityCategory.CONFIG,
        )


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities
) -> None:
    """Set up Breezart numbers."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = [
        BreezartTargetTemperatureNumber(coordinator),
        BreezartFanSpeedNumber(coordinator),
    ]
    
    async_add_entities(entities)
