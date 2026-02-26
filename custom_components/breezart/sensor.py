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
        enabled_default: bool = True,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"breezart_{coordinator.client.host}_{unique_suffix}"
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_entity_category = entity_category
        self._attr_state_class = state_class
        self._attr_entity_registry_enabled_default = enabled_default
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
    """Sensor that maps numeric values to text using a dictionary."""

    def __init__(
        self,
        coordinator: BreezartDataCoordinator,
        unique_suffix: str,
        name: str,
        key: str,
        value_map: dict[int, str],
        entity_category: EntityCategory | None = None,
        enabled_default: bool = True,
    ) -> None:
        """Initialize the text sensor."""
        super().__init__(
            coordinator, unique_suffix, name, key,
            entity_category=entity_category, state_class=None,
            enabled_default=enabled_default,
        )
        self._value_map = value_map

    @property
    def native_value(self) -> str | None:
        """Return the mapped text value."""
        if not self.coordinator.data:
            return None
        raw_value = self.coordinator.data.get(self._key)
        if raw_value is None:
            return None
        return self._value_map.get(raw_value, f"Неизвестно ({raw_value})")


class BreezartFilterSensor(BreezartSensor):
    """Sensor for filter pollution status with text representation."""

    def __init__(
        self,
        coordinator: BreezartDataCoordinator,
        unique_suffix: str,
        name: str,
        key: str,
    ) -> None:
        """Initialize the filter sensor."""
        super().__init__(
            coordinator, unique_suffix, name, key,
            unit=PERCENTAGE, entity_category=EntityCategory.DIAGNOSTIC,
            enabled_default=False,
        )

    @property
    def native_value(self) -> float | None:
        """Return the numeric pollution value."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self._key)

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return additional state attributes with text status."""
        if not self.coordinator.data:
            return None
        
        pollution = self.coordinator.data.get(self._key)
        if pollution is None:
            return {"status": "Нет данных"}
        
        # Map pollution percentage to status
        if pollution < 30:
            status = "Отличное"
        elif pollution < 60:
            status = "Хорошее"
        elif pollution < 85:
            status = "Требуется замена"
        else:
            status = "Забит"
        
        return {"status": status}


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
            enabled_default=False,
        ),
        BreezartSensor(
            coordinator, "temp_outdoor", "Температура на улице",
            "temp_outdoor", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS,
            enabled_default=False,
        ),
        BreezartSensor(
            coordinator, "temp_water", "Температура теплоносителя",
            "temp_water", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS,
            enabled_default=False,
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
            enabled_default=False,
        ),
        # --- Мощность ---
        BreezartSensor(
            coordinator, "power_consumption", "Потребляемая мощность",
            "power_consumption", SensorDeviceClass.POWER, UnitOfPower.WATT,
            enabled_default=False,
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
        # --- Дополнительная влажность ---
        BreezartSensor(
            coordinator, "humidity_supply", "Влажность на притоке",
            "humidity_supply", SensorDeviceClass.HUMIDITY, PERCENTAGE,
            enabled_default=False,
        ),
        BreezartSensor(
            coordinator, "humidity_room", "Влажность в помещении",
            "humidity_room", SensorDeviceClass.HUMIDITY, PERCENTAGE,
            enabled_default=False,
        ),
        BreezartSensor(
            coordinator, "humidity_outdoor", "Влажность уличного воздуха",
            "humidity_outdoor", SensorDeviceClass.HUMIDITY, PERCENTAGE,
            enabled_default=False,
        ),
        # --- Качество воздуха ---
        BreezartSensor(
            coordinator, "co2", "CO₂",
            "co2", SensorDeviceClass.CO2, "ppm",
            enabled_default=False,
        ),
        BreezartSensor(
            coordinator, "voc", "VOC (загрязнённость воздуха)",
            "voc", unit="ppb",
            enabled_default=False,
        ),
        # --- Состояние фильтров ---
        BreezartFilterSensor(coordinator, "filter1_pollution", "Фильтр 1", "filter1_pollution"),
        BreezartFilterSensor(coordinator, "filter2_pollution", "Фильтр 2", "filter2_pollution"),
        BreezartFilterSensor(coordinator, "filter3_pollution", "Фильтр 3", "filter3_pollution"),
        BreezartFilterSensor(coordinator, "filter4_pollution", "Фильтр 4", "filter4_pollution"),
    ]

    async_add_entities(entities)
