"""Breezart TCP client and data coordinator."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DELIMITER,
    DOMAIN,
    ERROR_PREFIX,
    NO_DATA_VALUE,
    POWER_OFF,
    POWER_ON,
    REQ_GET_PROPERTIES,
    REQ_GET_SENSORS,
    REQ_GET_STATE,
    REQ_SET_FAN_SPEED,
    REQ_SET_MODE,
    REQ_SET_POWER,
    REQ_SET_TEMP,
    RESP_OK,
    RESP_PROPERTIES,
    RESP_SENSORS,
    RESP_STATE,
)

_LOGGER = logging.getLogger(__name__)


def _dec_to_hex(value: int) -> str:
    """Convert decimal integer to hex string (like breezart-client decToHex)."""
    if not isinstance(value, int) or value < 0 or value > 65535:
        raise ValueError(f"Value must be a positive integer <= 65535, got {value}")
    return format(value, "x")


def _hex_to_dec(hex_str: str) -> int:
    """Convert hex string to unsigned decimal."""
    return int(hex_str, 16)


def _hex_to_dec_sign(hex_str: str) -> int:
    """Convert hex string to signed decimal (signed 16-bit)."""
    val = int(hex_str, 16)
    if val & 0x8000:
        val -= 0x10000
    return val


def _parse_bits(hex_str: str, from_bit: int, to_bit: int | None = None) -> int:
    """Extract bits from a hex string (like breezart-client parceBits)."""
    if to_bit is None:
        to_bit = from_bit
    if hex_str == "0":
        return 0
    num = int(hex_str, 16)
    bits = format(num, "016b")[::-1]
    extracted = bits[from_bit: to_bit + 1][::-1]
    return int(extracted, 2)


class BreezartTCPClient:
    """TCP client for Breezart ventilation system (native protocol, port 1560)."""

    def __init__(
        self,
        host: str,
        port: int,
        password: int | str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the TCP client."""
        self.host = host
        self.port = port
        self.password = int(password)
        self.timeout = timeout
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

        # Device properties (populated on first connect)
        self.temp_min: int = 15
        self.temp_max: int = 30
        self.speed_min: int = 1
        self.speed_max: int = 10
        self.has_cooler: bool = False
        self.has_humidifier: bool = False
        self.firmware_ver: int | None = None
        self.protocol_ver: str | None = None

    def _build_request(self, request_type: str, data: int | None = None) -> str:
        """Build a request string: requestType_password[_data]."""
        parts = [request_type, _dec_to_hex(self.password)]
        if data is not None:
            parts.append(_dec_to_hex(data))
        return DELIMITER.join(parts)

    def _split_response(self, message: str) -> list[str]:
        """Split response by delimiter, removing empty parts."""
        return [v for v in message.split(DELIMITER) if v]

    def _check_error(self, parts: list[str]) -> None:
        """Raise if response indicates an error."""
        if parts and parts[0] in ERROR_PREFIX:
            raise PermissionError(f"Breezart error: {ERROR_PREFIX[parts[0]]} ({DELIMITER.join(parts)})")

    async def connect(self) -> None:
        """Open TCP connection."""
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout,
            )
            _LOGGER.info("Connected to Breezart at %s:%d", self.host, self.port)
        except (OSError, asyncio.TimeoutError) as err:
            _LOGGER.error("Failed to connect to Breezart: %s", err)
            raise

    async def disconnect(self) -> None:
        """Close TCP connection."""
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None

    async def _send(self, request: str) -> list[str]:
        """Send a request and return split response."""
        if not self._writer or not self._reader:
            raise ConnectionError("Not connected to Breezart")

        _LOGGER.debug("Breezart TX: %s", request)
        # Send WITHOUT newline (like breezart-client)
        self._writer.write(request.encode())
        await self._writer.drain()

        # Read response with timeout (breezart may not send \n)
        response = ""
        try:
            # Try to read until newline first
            try:
                raw = await asyncio.wait_for(
                    self._reader.readuntil(b'\n'), 
                    timeout=self.timeout
                )
                response = raw.decode().strip()
            except asyncio.LimitOverrunError:
                # Response too long without newline, read what's available
                raw = await asyncio.wait_for(
                    self._reader.read(4096),
                    timeout=self.timeout
                )
                response = raw.decode().strip()
        except asyncio.TimeoutError:
            raise TimeoutError(f"No response for request: {request}")
        except Exception as e:
            raise ConnectionError(f"Error reading response: {e}")

        if not response:
            raise TimeoutError(f"Empty response for request: {request}")

        _LOGGER.debug("Breezart RX: %s", response)
        parts = self._split_response(response)
        self._check_error(parts)
        return parts

    async def get_properties(self) -> None:
        """Read device properties (VPr07). Called once after connect."""
        req = self._build_request(REQ_GET_PROPERTIES)
        parts = await self._send(req)

        if not parts or parts[0] != RESP_PROPERTIES:
            raise ValueError(f"Unexpected properties response: {parts}")

        # bitTempr: Bit 7-0 TempMin, Bit 15-8 TempMax
        self.temp_min = _parse_bits(parts[1], 0, 7)
        self.temp_max = _parse_bits(parts[1], 8, 15)
        # bitSpeed: Bit 7-0 SpeedMin, Bit 15-8 SpeedMax
        self.speed_min = _parse_bits(parts[2], 0, 7)
        self.speed_max = _parse_bits(parts[2], 8, 15)
        # bitMisc: Bit 14 IsCooler, Bit 13 IsHumid
        self.has_cooler = bool(_parse_bits(parts[4], 14))
        self.has_humidifier = bool(_parse_bits(parts[4], 13))
        # BitPrt: protocol version
        sub = _parse_bits(parts[5], 0, 7)
        major = _parse_bits(parts[5], 8, 15)
        self.protocol_ver = f"{major}.{sub}"
        # BitVerContr: firmware
        self.firmware_ver = _hex_to_dec(parts[7])

        _LOGGER.info(
            "Breezart properties: T=%d..%d°C, Speed=%d..%d, fw=%s, proto=%s",
            self.temp_min, self.temp_max,
            self.speed_min, self.speed_max,
            self.firmware_ver, self.protocol_ver,
        )

    async def get_state(self) -> dict[str, Any]:
        """Read current state (VSt07)."""
        req = self._build_request(REQ_GET_STATE)
        parts = await self._send(req)

        if not parts or parts[0] != RESP_STATE:
            raise ValueError(f"Unexpected state response: {parts}")

        # bitState
        pwr_btn_state = _parse_bits(parts[1], 0)
        is_warn_err = bool(_parse_bits(parts[1], 1))
        is_fatal_err = bool(_parse_bits(parts[1], 2))
        danger_overheat = bool(_parse_bits(parts[1], 3))
        change_filter = bool(_parse_bits(parts[1], 5))
        mode_set = _parse_bits(parts[1], 6, 8)

        # bitMode
        unit_state = _parse_bits(parts[2], 0, 1)
        mode = _parse_bits(parts[2], 3, 5)

        # bitTempr: Bit 7-0 current (signed), Bit 15-8 target
        tempr_raw = _parse_bits(parts[3], 0, 7)
        tempr = tempr_raw if tempr_raw < 128 else tempr_raw - 256
        temper_target = _parse_bits(parts[3], 8, 15)

        # bitHumid
        humid = _parse_bits(parts[4], 0, 7)
        humid = None if humid == 255 else humid

        # bitSpeed
        speed = _parse_bits(parts[5], 0, 3)
        speed_target = _parse_bits(parts[5], 4, 7)
        speed_fact = _parse_bits(parts[5], 8, 15)
        speed_fact = None if speed_fact == 255 else speed_fact

        # bitMisc
        color_msg = _parse_bits(parts[6], 4, 5)
        color_ind = _parse_bits(parts[6], 6, 7)
        filter_dust = _parse_bits(parts[6], 8, 15)
        filter_dust = None if filter_dust == 255 else filter_dust

        msg = parts[10] if len(parts) > 10 else None

        return {
            "power": bool(pwr_btn_state),
            "unit_state": unit_state,
            "mode": mode,
            "mode_set": mode_set,
            "temperature": float(tempr),
            "temperature_target": float(temper_target),
            "humidity": humid,
            "speed": speed,
            "speed_target": speed_target,
            "speed_fact": speed_fact,
            "filter_dust": filter_dust,
            "is_warn_err": is_warn_err,
            "is_fatal_err": is_fatal_err,
            "danger_overheat": danger_overheat,
            "change_filter": change_filter,
            "color_msg": color_msg,
            "color_ind": color_ind,
            "msg": msg,
        }

    async def get_sensors(self) -> dict[str, Any]:
        """Read sensor values (VSens)."""
        req = self._build_request(REQ_GET_SENSORS)
        parts = await self._send(req)

        if not parts or parts[0] != RESP_SENSORS:
            raise ValueError(f"Unexpected sensors response: {parts}")

        def _parse_temp_sensor(val: str) -> float | None:
            if val == "fb07":
                return None
            return _hex_to_dec_sign(val) / 10.0

        def _parse_sensor(val: str) -> float | None:
            if val == "fb07":
                return None
            return float(_hex_to_dec(val))

        t_inf = _parse_temp_sensor(parts[1]) if len(parts) > 1 else None
        t_room = _parse_sensor(parts[3]) if len(parts) > 3 else None
        t_out = _parse_temp_sensor(parts[5]) if len(parts) > 5 else None
        t_hf = _parse_sensor(parts[7]) if len(parts) > 7 else None
        pwr = _parse_sensor(parts[8]) if len(parts) > 8 else None

        return {
            "temp_supply": t_inf,
            "temp_room": t_room,
            "temp_outdoor": t_out,
            "temp_water": t_hf,
            "power_consumption": pwr,
        }

    async def set_power(self, on: bool) -> None:
        """Turn device on or off (VWPwr)."""
        data = POWER_ON if on else POWER_OFF
        req = self._build_request(REQ_SET_POWER, data)
        parts = await self._send(req)
        if not parts or parts[0] != RESP_OK:
            raise ValueError(f"Unexpected set_power response: {parts}")

    async def set_temperature(self, temperature: int) -> None:
        """Set target temperature (VWTmp). Must be integer degrees."""
        req = self._build_request(REQ_SET_TEMP, temperature)
        parts = await self._send(req)
        if not parts or parts[0] != RESP_OK:
            raise ValueError(f"Unexpected set_temperature response: {parts}")

    async def set_fan_speed(self, speed: int) -> None:
        """Set fan speed 0-10 (VWSpd)."""
        req = self._build_request(REQ_SET_FAN_SPEED, speed)
        parts = await self._send(req)
        if not parts or parts[0] != RESP_OK:
            raise ValueError(f"Unexpected set_fan_speed response: {parts}")

    async def set_mode(self, mode: int) -> None:
        """Set work mode (VWFtr). 1=Heat, 2=Cool, 3=Auto, 4=Vent."""
        req = self._build_request(REQ_SET_MODE, mode)
        parts = await self._send(req)
        if not parts or parts[0] != RESP_OK:
            raise ValueError(f"Unexpected set_mode response: {parts}")


class BreezartDataCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that polls Breezart for state and sensor data."""

    def __init__(self, hass: HomeAssistant, client: BreezartTCPClient) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        self._properties_loaded = False

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch latest data from Breezart."""
        try:
            if not self.client._writer:
                await self.client.connect()

            if not self._properties_loaded:
                await self.client.get_properties()
                self._properties_loaded = True

            state = await self.client.get_state()
            sensors = await self.client.get_sensors()

            data = {**state, **sensors}

            data["temp_min"] = self.client.temp_min
            data["temp_max"] = self.client.temp_max
            data["speed_min"] = self.client.speed_min
            data["speed_max"] = self.client.speed_max
            data["has_cooler"] = self.client.has_cooler
            data["has_humidifier"] = self.client.has_humidifier
            data["firmware_ver"] = self.client.firmware_ver
            data["protocol_ver"] = self.client.protocol_ver

            _LOGGER.debug("Breezart update: %s", data)
            return data

        except (ConnectionError, OSError, TimeoutError) as err:
            self._properties_loaded = False
            await self.client.disconnect()
            raise UpdateFailed(f"Connection error: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Breezart: {err}") from err
