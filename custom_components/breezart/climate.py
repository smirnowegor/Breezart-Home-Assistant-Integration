"""Climate platform for Breezart integration."""
from __future__ import annotations

import logging
import time
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
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MODE_MAP
from .coordinator import BreezartDataCoordinator

_LOGGER = logging.getLogger(__name__)
_OPTIMISTIC_HOLD_SECONDS = 6


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
    _attr_fan_modes = ["1", "2", "3", "4", "5", "6", "7", "8"]

    def __init__(self, coordinator: BreezartDataCoordinator) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"breezart_{coordinator.client.host}_climate"
        self._attr_min_temp = float(coordinator.client.temp_min)
        self._attr_max_temp = float(coordinator.client.temp_max)
        self._attr_target_temperature_step = 1.0
        # Optimistic state — applied immediately on command, confirmed by next poll
        self._optimistic_target_temp: float | None = None
        self._optimistic_fan_mode: str | None = None
        self._optimistic_hvac_mode: HVACMode | None = None
        self._optimistic_set_time: float = 0.0

    def _handle_coordinator_update(self) -> None:
        """Clear optimistic state only after hold period expires.
        
        Keeps optimistic value visible for _OPTIMISTIC_HOLD_SECONDS after
        a command is sent, giving the device time to apply and confirm.
        """
        if time.monotonic() - self._optimistic_set_time > _OPTIMISTIC_HOLD_SECONDS:
            self._optimistic_target_temp = None
            self._optimistic_fan_mode = None
            self._optimistic_hvac_mode = None
        super()._handle_coordinator_update()

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature.
        
        Prefer temp_supply (приточный воздух from VSens).
        Fall back to temperature (подача from VSt07) if not available.
        """
        if not self.coordinator.data:
            return None
        temp_supply = self.coordinator.data.get("temp_supply")
        if temp_supply is not None:
            return temp_supply
        return self.coordinator.data.get("temperature")

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        if self._optimistic_target_temp is not None:
            return self._optimistic_target_temp
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("temperature_target")

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        if self._optimistic_hvac_mode is not None:
            return self._optimistic_hvac_mode
        if not self.coordinator.data:
            return HVACMode.OFF

        power = self.coordinator.data.get("power", False)
        if not power:
            return HVACMode.OFF

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

        unit_state = self.coordinator.data.get("unit_state", 0)
        if unit_state == 0:
            return HVACAction.OFF
        elif unit_state == 1:
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
        if self._optimistic_fan_mode is not None:
            return self._optimistic_fan_mode
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
        # Optimistic: update UI immediately, device confirms within hold period
        self._optimistic_target_temp = float(temperature)
        self._optimistic_set_time = time.monotonic()
        self.async_write_ha_state()
        try:
            await self.coordinator.client.set_temperature(int(temperature))
            _LOGGER.debug("Set temperature to %d°C", int(temperature))
        except Exception as err:
            _LOGGER.error("Failed to set temperature: %s", err)
            self._optimistic_target_temp = None
            self.async_write_ha_state()
            return
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        self._optimistic_hvac_mode = hvac_mode
        self._optimistic_set_time = time.monotonic()
        self.async_write_ha_state()
        try:
            if hvac_mode == HVACMode.OFF:
                await self.coordinator.client.set_power(False)
            else:
                if not self.coordinator.data.get("power", False):
                    await self.coordinator.client.set_power(True)
                if hvac_mode == HVACMode.HEAT:
                    await self.coordinator.client.set_mode(0)
                elif hvac_mode == HVACMode.COOL:
                    await self.coordinator.client.set_mode(1)
                elif hvac_mode == HVACMode.AUTO:
                    await self.coordinator.client.set_mode(2)
                elif hvac_mode == HVACMode.FAN_ONLY:
                    await self.coordinator.client.set_mode(3)
        except Exception as err:
            _LOGGER.error("Failed to set HVAC mode: %s", err)
            self._optimistic_hvac_mode = None
            self.async_write_ha_state()
            return
        await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new fan mode (speed)."""
        try:
            speed = int(fan_mode)
        except ValueError:
            return
        # Optimistic: update UI immediately, device confirms within hold period
        self._optimistic_fan_mode = fan_mode
        self._optimistic_set_time = time.monotonic()
        self.async_write_ha_state()
        try:
            await self.coordinator.client.set_fan_speed(speed)
            _LOGGER.debug("Set fan speed to %d", speed)
        except Exception as err:
            _LOGGER.error("Failed to set fan speed: %s", err)
            self._optimistic_fan_mode = None
            self.async_write_ha_state()
            return
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        """Turn on."""
        self._optimistic_hvac_mode = HVACMode.HEAT
        self._optimistic_set_time = time.monotonic()
        self.async_write_ha_state()
        try:
            await self.coordinator.client.set_power(True)
        except Exception as err:
            _LOGGER.error("Failed to turn on: %s", err)
            self._optimistic_hvac_mode = None
            self.async_write_ha_state()
            return
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        """Turn off."""
        self._optimistic_hvac_mode = HVACMode.OFF
        self._optimistic_set_time = time.monotonic()
        self.async_write_ha_state()
        try:
            await self.coordinator.client.set_power(False)
        except Exception as err:
            _LOGGER.error("Failed to turn off: %s", err)
            self._optimistic_hvac_mode = None
            self.async_write_ha_state()
            return
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
