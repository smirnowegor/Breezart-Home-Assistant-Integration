"""Sensor platform for Breezart integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COLOR_IND_MAP, COLOR_MSG_MAP, DOMAIN, MODE_MAP, MODE_SET_MAP, UNIT_STATE_MAP
from .coordinator import BreezartDataCoordinator


class BreezartSensor(CoordinatorEntity[BreezartDataCoordinator], SensorEntity):
    """Base class for Breezart sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BreezartDataCoordinator,
        unique_suffix: str,
        name: str,
        key: str,
        device_class: SensorDeviceClass | None = None,
        unit: str | None = None,
        entity_category: EntityCategory | None = None,
        state_class: SensorStateClass | None = SensorStateClass.MEASUREMENT,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"breezart_{coordinator.client.host}_{unique_suffix}"
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_entity_category = entity_category
        self._attr_state_class = state_class
        self._key = key

    @property
    def native_value(self) -> float | int | str | None:
        """Return the sensor value from coordinator data."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self._key)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.client.host)},
            name="Breezart",
            manufacturer="Breezart",
            model="550 Aqua",
            sw_version=str(self.coordinator.client.firmware_ver or ""),
        )


class BreezartTextSensor(BreezartSensor):
    """Sensor whose value is mapped through a dict."""

    def __init__(
        self,
        coordinator: BreezartDataCoordinator,
        unique_suffix: str,
        name: str,
        key: str,
        value_map: dict,
        entity_category: EntityCategory | None = None,
    ) -> None:
        """Initialize."""
        super().__init__(
            coordinator,
            unique_suffix,
            name,
            key,
            entity_category=entity_category,
            state_class=None,
        )
        self._value_map = value_map

    @property
    def native_value(self) -> str | None:
        """Return mapped string value."""
        if not self.coordinator.data:
            return None
        raw = self.coordinator.data.get(self._key)
        if raw is None:
            return None
        return self._value_map.get(raw, f"Unknown ({raw})")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Breezart sensor entities."""
    coordinator: BreezartDataCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[SensorEntity] = [
        # --- Температуры ---
        BreezartSensor(
            coordinator, "temperature", "Температура подачи",
            "temperature", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS,
        ),
        BreezartSensor(
            coordinator, "temp_supply", "Температура приточного воздуха",
            "temp_supply", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS,
        ),
        BreezartSensor(
            coordinator, "temp_room", "Температура в помещении",
            "temp_room", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS,
        ),
        BreezartSensor(
            coordinator, "temp_outdoor", "Температура на улице",
            "temp_outdoor", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS,
        ),
        BreezartSensor(
            coordinator, "temp_water", "Температура теплоносителя",
            "temp_water", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS,
        ),
        BreezartSensor(
            coordinator, "temperature_target", "Заданная температура",
            "temperature_target", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        # --- Скорость ---
        BreezartSensor(
            coordinator, "speed", "Скорость вентилятора",
            "speed", unit=None,
        ),
        BreezartSensor(
            coordinator, "speed_target", "Заданная скорость",
            "speed_target", unit=None,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        BreezartSensor(
            coordinator, "speed_fact", "Фактическая скорость",
            "speed_fact", unit=PERCENTAGE,
        ),
        # --- Мощность ---
        BreezartSensor(
            coordinator, "power_consumption", "Потребляемая мощность",
            "power_consumption", SensorDeviceClass.POWER, UnitOfPower.WATT,
        ),
        # --- Фильтр ---
        BreezartSensor(
            coordinator, "filter_dust", "Загрязнённость фильтра",
            "filter_dust", unit=PERCENTAGE,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        # --- Влажность ---
        BreezartSensor(
            coordinator, "humidity", "Влажность",
            "humidity", SensorDeviceClass.HUMIDITY, PERCENTAGE,
        ),
        # --- Состояние ---
        BreezartTextSensor(
            coordinator, "unit_state", "Состояние установки",
            "unit_state", UNIT_STATE_MAP,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        BreezartTextSensor(
            coordinator, "mode", "Режим работы",
            "mode", MODE_MAP,
        ),
        BreezartTextSensor(
            coordinator, "mode_set", "Заданный режим",
            "mode_set", MODE_SET_MAP,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        BreezartTextSensor(
            coordinator, "color_ind", "Индикатор питания",
            "color_ind", COLOR_IND_MAP,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        BreezartTextSensor(
            coordinator, "color_msg", "Статус сообщения",
            "color_msg", COLOR_MSG_MAP,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        # --- Сообщение устройства ---
        BreezartSensor(
            coordinator, "msg", "Сообщение устройства",
            "msg", state_class=None,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        # --- Прошивка/протокол ---
        BreezartSensor(
            coordinator, "firmware_ver", "Версия прошивки",
            "firmware_ver", state_class=None,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        BreezartSensor(
            coordinator, "protocol_ver", "Версия протокола",
            "protocol_ver", state_class=None,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
    ]

    async_add_entities(entities)
