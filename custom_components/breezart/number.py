"""Number platform for Breezart integration."""
from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BreezartDataCoordinator


class BreezartTargetTemperature(CoordinatorEntity[BreezartDataCoordinator], NumberEntity):
    """Target temperature control for Breezart."""

    _attr_has_entity_name = True
    _attr_name = "Заданная температура"
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_step = 1.0

    def __init__(self, coordinator: BreezartDataCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"breezart_{coordinator.client.host}_target_temp"
        self._attr_native_min_value = float(coordinator.client.temp_min)
        self._attr_native_max_value = float(coordinator.client.temp_max)

    @property
    def native_value(self) -> float | None:
        """Return the current target temperature."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("temperature_target")

    async def async_set_native_value(self, value: float) -> None:
        """Set target temperature via protocol."""
        await self.coordinator.client.set_temperature(int(value))
        await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.client.host)},
            name="Breezart",
            manufacturer="Breezart",
            model="550 Aqua",
        )


class BreezartFanSpeed(CoordinatorEntity[BreezartDataCoordinator], NumberEntity):
    """Fan speed control for Breezart."""

    _attr_has_entity_name = True
    _attr_name = "Скорость вентилятора"
    _attr_native_step = 1.0

    def __init__(self, coordinator: BreezartDataCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"breezart_{coordinator.client.host}_fan_speed"
        self._attr_native_min_value = float(coordinator.client.speed_min)
        self._attr_native_max_value = float(coordinator.client.speed_max)

    @property
    def native_value(self) -> float | None:
        """Return the current fan speed target."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("speed_target")

    async def async_set_native_value(self, value: float) -> None:
        """Set fan speed via protocol."""
        await self.coordinator.client.set_fan_speed(int(value))
        await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.client.host)},
            name="Breezart",
            manufacturer="Breezart",
            model="550 Aqua",
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Breezart number entities."""
    coordinator: BreezartDataCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities([
        BreezartTargetTemperature(coordinator),
        BreezartFanSpeed(coordinator),
    ])
