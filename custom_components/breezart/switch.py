"""Switch platform for Breezart integration."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.entity import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, REG_POWER
from .coordinator import BreezartDataCoordinator


class BreezartPowerSwitch(CoordinatorEntity, SwitchEntity):
    """Switch for Breezart power."""

    def __init__(self, coordinator: BreezartDataCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_name = "Breezart Power"
        self._attr_unique_id = f"{coordinator.client.host}_power"
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self) -> bool:
        """Return True if the device is on."""
        if self.coordinator.data:
            status = self.coordinator.data.get("status", 0)
            return status > 0
        return False

    async def async_turn_on(self) -> None:
        """Turn the device on."""
        await self.coordinator.write_register(REG_POWER, 1)
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        """Turn the device off."""
        await self.coordinator.write_register(REG_POWER, 0)
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


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities
) -> None:
    """Set up Breezart switches."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = [BreezartPowerSwitch(coordinator)]
    
    async_add_entities(entities)
