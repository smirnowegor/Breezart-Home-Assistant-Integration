"""Binary sensor platform for Breezart integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BreezartDataCoordinator


class BreezartBinarySensor(CoordinatorEntity[BreezartDataCoordinator], BinarySensorEntity):
    """Base binary sensor for Breezart."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BreezartDataCoordinator,
        unique_suffix: str,
        name: str,
        key: str,
        device_class: BinarySensorDeviceClass | None = None,
        entity_category: EntityCategory | None = None,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"breezart_{coordinator.client.host}_{unique_suffix}"
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_entity_category = entity_category
        self._key = key

    @property
    def is_on(self) -> bool | None:
        """Return True if the binary sensor is on."""
        if not self.coordinator.data:
            return None
        return bool(self.coordinator.data.get(self._key, False))

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
    """Set up Breezart binary sensor entities."""
    coordinator: BreezartDataCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities([
        BreezartBinarySensor(
            coordinator, "is_warn_err", "Предупреждение",
            "is_warn_err",
            BinarySensorDeviceClass.PROBLEM,
            EntityCategory.DIAGNOSTIC,
        ),
        BreezartBinarySensor(
            coordinator, "is_fatal_err", "Критическая ошибка",
            "is_fatal_err",
            BinarySensorDeviceClass.PROBLEM,
            EntityCategory.DIAGNOSTIC,
        ),
        BreezartBinarySensor(
            coordinator, "danger_overheat", "Угроза перегрева",
            "danger_overheat",
            BinarySensorDeviceClass.HEAT,
            EntityCategory.DIAGNOSTIC,
        ),
        BreezartBinarySensor(
            coordinator, "change_filter", "Требуется замена фильтра",
            "change_filter",
            BinarySensorDeviceClass.PROBLEM,
            EntityCategory.DIAGNOSTIC,
        ),
        BreezartBinarySensor(
            coordinator, "power", "Установка включена",
            "power",
            BinarySensorDeviceClass.RUNNING,
        ),
    ])
