"""Switch platform for Breezart integration."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BreezartDataCoordinator


class BreezartPowerSwitch(CoordinatorEntity[BreezartDataCoordinator], SwitchEntity):
    """Power switch for Breezart ventilation unit."""

    _attr_has_entity_name = True
    _attr_name = "Питание"

    def __init__(self, coordinator: BreezartDataCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"breezart_{coordinator.client.host}_power"

    @property
    def is_on(self) -> bool:
        """Return True if the unit is on (PwrBtnState == 1)."""
        if not self.coordinator.data:
            return False
        return bool(self.coordinator.data.get("power", False))

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the unit on."""
        await self.coordinator.client.set_power(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the unit off."""
        await self.coordinator.client.set_power(False)
        await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
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
    """Set up Breezart switch entities."""
    coordinator: BreezartDataCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([BreezartPowerSwitch(coordinator)])
