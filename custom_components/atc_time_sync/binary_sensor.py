"""Binary sensor platform for ATC Time Sync."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    broadcaster = data["broadcaster"]

    async_add_entities([
        BroadcastStatusSensor(entry, broadcaster),
    ])


class BroadcastStatusSensor(BinarySensorEntity):
    """Binary sensor showing whether the beacon is broadcasting."""

    _attr_has_entity_name = True
    _attr_name = "Broadcasting"
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:bluetooth-audio"

    def __init__(self, entry: ConfigEntry, broadcaster) -> None:
        """Initialize the sensor."""
        self._entry = entry
        self._broadcaster = broadcaster
        self._attr_unique_id = f"{entry.entry_id}_broadcasting"

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "ATC Time Sync Beacon",
            "manufacturer": "ATC_MiThermometer",
            "model": "BTHome Time Broadcaster",
            "sw_version": "0.1.0",
        }

    @property
    def is_on(self) -> bool:
        """Return true if broadcasting."""
        return self._broadcaster.is_running

    async def async_update(self) -> None:
        """Update sensor state."""
        pass
