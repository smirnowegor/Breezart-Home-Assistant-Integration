"""Climate platform for Breezart integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MODE_MAP
from .coordinator import BreezartDataCoordinator


class BreezartClimate(CoordinatorEntity[BreezartDataCoordinator], ClimateEntity):
    """Breezart climate entity (thermostat)."""

    _attr_has_entity_name = True
    _attr_name = "Климат"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.FAN_ONLY, HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO]
    
    # Fan modes based on speed (1-10)
    _attr_fan_modes = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]

    def __init__(self, coordinator: BreezartDataCoordinator) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"breezart_{coordinator.client.host}_climate"
        self._attr_min_temp = float(coordinator.client.temp_min)
        self._attr_max_temp = float(coordinator.client.temp_max)
        self._attr_target_temperature_step = 1.0

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("temperature")

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("temperature_target")

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        if not self.coordinator.data:
            return HVACMode.OFF
        
        power = self.coordinator.data.get("power", False)
        if not power:
            return HVACMode.OFF
        
        # Map Breezart mode to HVAC mode
        mode = self.coordinator.data.get("mode", 0)
        mode_name = MODE_MAP.get(mode, "").lower()
        
        if "обогрев" in mode_name or "нагрев" in mode_name:
            return HVACMode.HEAT
        elif "охлаждение" in mode_name:
            return HVACMode.COOL
        elif "авто" in mode_name:
            return HVACMode.AUTO
        else:
            return HVACMode.FAN_ONLY

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return current HVAC action."""
        if not self.coordinator.data:
            return None
        
        power = self.coordinator.data.get("power", False)
        if not power:
            return HVACAction.OFF
        
        # Check unit state
        unit_state = self.coordinator.data.get("unit_state", 0)
        if unit_state == 0:  # Off
            return HVACAction.OFF
        elif unit_state == 1:  # On
            mode = self.coordinator.data.get("mode", 0)
            mode_name = MODE_MAP.get(mode, "").lower()
            
            if "обогрев" in mode_name or "нагрев" in mode_name:
                return HVACAction.HEATING
            elif "охлаждение" in mode_name:
                return HVACAction.COOLING
            else:
                return HVACAction.FAN
        else:
            return HVACAction.IDLE

    @property
    def fan_mode(self) -> str | None:
        """Return current fan mode (speed)."""
        if not self.coordinator.data:
            return None
        speed = self.coordinator.data.get("speed_target")
        if speed is not None:
            return str(speed)
        return None

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        
        await self.coordinator.client.set_temperature(int(temperature))
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.client.set_power(False)
        else:
            # Turn on if off
            if not self.coordinator.data.get("power", False):
                await self.coordinator.client.set_power(True)
            
            # Map HVAC mode to Breezart mode
            # Mode values: 0=Heat, 1=Cool, 2=Auto, 3=Vent
            if hvac_mode == HVACMode.HEAT:
                await self.coordinator.client.set_mode(0)
            elif hvac_mode == HVACMode.COOL:
                await self.coordinator.client.set_mode(1)
            elif hvac_mode == HVACMode.AUTO:
                await self.coordinator.client.set_mode(2)
            elif hvac_mode == HVACMode.FAN_ONLY:
                await self.coordinator.client.set_mode(3)
        
        await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new fan mode (speed)."""
        try:
            speed = int(fan_mode)
            await self.coordinator.client.set_fan_speed(speed)
            await self.coordinator.async_request_refresh()
        except ValueError:
            pass

    async def async_turn_on(self) -> None:
        """Turn on."""
        await self.coordinator.client.set_power(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        """Turn off."""
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
    """Set up Breezart climate entity."""
    coordinator: BreezartDataCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([BreezartClimate(coordinator)])
