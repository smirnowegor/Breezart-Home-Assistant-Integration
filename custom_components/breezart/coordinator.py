"""Breezart TCP client and data coordinator."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    REG_CURRENT_TEMP,
    REG_FAN_SPEED_CURRENT,
    REG_OUTDOOR_TEMP,
    REG_STATUS,
    REG_WATER_TEMP,
)

_LOGGER = logging.getLogger(__name__)


class BreezartTCPClient:
    """TCP client for Breezart ventilation system."""

    def __init__(
        self,
        host: str,
        port: int,
        password: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the TCP client."""
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._authorized = False

    async def connect(self) -> None:
        """Connect to Breezart device."""
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=self.timeout
            )
            _LOGGER.info("Connected to Breezart at %s:%d", self.host, self.port)
        except (OSError, asyncio.TimeoutError) as err:
            _LOGGER.error("Failed to connect to Breezart: %s", err)
            raise

    async def disconnect(self) -> None:
        """Disconnect from Breezart device."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
            self._writer = None
            self._reader = None
        self._authorized = False

    async def authorize(self) -> None:
        """Send password authorization."""
        if not self._writer:
            raise ConnectionError("Not connected to Breezart")
        
        # TODO: Implement actual authorization protocol based on breezart-client
        # This is a placeholder - need to implement the actual protocol
        _LOGGER.info("Authorizing with password: %s", self.password)
        self._authorized = True

    async def read_register(self, address: int) -> int:
        """Read a single register."""
        if not self._authorized:
            await self.authorize()
        
        # TODO: Implement actual register reading based on breezart-client
        # This is a placeholder - need to implement the actual protocol
        _LOGGER.debug("Reading register %d", address)
        
        # Return mock data for now
        if address == REG_STATUS:
            return 1  # Work mode
        elif address == REG_CURRENT_TEMP:
            return 220  # 22.0°C
        elif address == REG_FAN_SPEED_CURRENT:
            return 50  # 50%
        elif address == REG_WATER_TEMP:
            return 180  # 18.0°C
        elif address == REG_OUTDOOR_TEMP:
            return 150  # 15.0°C
        else:
            return 0

    async def write_register(self, address: int, value: int) -> None:
        """Write a single register."""
        if not self._authorized:
            await self.authorize()
        
        # TODO: Implement actual register writing based on breezart-client
        # This is a placeholder - need to implement the actual protocol
        _LOGGER.info("Writing register %d = %d", address, value)


class BreezartDataCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Data coordinator for Breezart."""

    def __init__(self, hass: HomeAssistant, client: BreezartTCPClient) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data via client."""
        try:
            if not self.client._reader:
                await self.client.connect()

            # Read all registers
            data = {
                "status": await self.client.read_register(REG_STATUS),
                "current_temperature": await self.client.read_register(REG_CURRENT_TEMP),
                "fan_speed_current": await self.client.read_register(REG_FAN_SPEED_CURRENT),
                "water_temperature": await self.client.read_register(REG_WATER_TEMP),
                "outdoor_temperature": await self.client.read_register(REG_OUTDOOR_TEMP),
            }
            
            _LOGGER.debug("Breezart data: %s", data)
            return data
            
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Breezart: {err}")

    async def write_register(self, address: int, value: int) -> None:
        """Write a register."""
        await self.client.write_register(address, value)
